from decimal import Decimal
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from core.models import audit
from core.permissions import ADMIN, RECEPTION, allowed
from quartos.models import Room, RoomBlock
from .models import Reservation

ACTIVE = [Reservation.Status.PENDING, Reservation.Status.CONFIRMED, Reservation.Status.IN_HOUSE]


def require_operator(actor):
    if not allowed(actor, ADMIN, RECEPTION):
        raise PermissionDenied


def conflicts(room_id, start, end, exclude=None):
    return Reservation.objects.filter(room_id=room_id, status__in=ACTIVE, start__lt=end, end__gt=start).exclude(pk=exclude)


def available_rooms(start, end, category="", exclude=None):
    if end <= start:
        raise ValidationError("A saída precisa ser posterior à entrada.")
    rooms = Room.objects.filter(active=True, status=Room.Status.READY)
    occupied = Reservation.objects.filter(status__in=ACTIVE, start__lt=end, end__gt=start).exclude(pk=exclude)
    blocks = RoomBlock.objects.filter(active=True, start__lt=end, end__gt=start)
    rooms = rooms.exclude(pk__in=occupied.values("room_id")).exclude(pk__in=blocks.values("room_id"))
    if start <= timezone.localdate():
        rooms = rooms.exclude(pk__in=Reservation.objects.filter(status=Reservation.Status.IN_HOUSE).exclude(pk=exclude).values("room_id"))
    return rooms.filter(category=category) if category else rooms


def validate_availability(room, start, end, exclude=None):
    if not room.active or room.status != Room.Status.READY:
        raise ValidationError("O quarto não está liberado para uso. Confira a situação operacional.")
    if conflicts(room.pk, start, end, exclude).exists():
        raise ValidationError("Este quarto já tem uma reserva nesse período. Escolha outro quarto ou altere as datas.")
    if RoomBlock.objects.filter(room=room, active=True, start__lt=end, end__gt=start).exists():
        raise ValidationError("Existe um bloqueio de manutenção para esse quarto no período.")
    if start <= timezone.localdate() and Reservation.objects.filter(room=room, status=Reservation.Status.IN_HOUSE).exclude(pk=exclude).exists():
        raise ValidationError("O quarto ainda está ocupado. Registre a saída e a limpeza antes de liberar.")


@transaction.atomic
def create_reservation(*, actor, room, guest, start, end, people, notes="", status=Reservation.Status.CONFIRMED):
    require_operator(actor)
    room = Room.objects.select_for_update().get(pk=room.pk)
    if start < timezone.localdate():
        raise ValidationError("Uma nova reserva não pode começar no passado.")
    if status not in (Reservation.Status.PENDING, Reservation.Status.CONFIRMED):
        raise ValidationError("Escolha Pendente ou Confirmada para a nova reserva.")
    item = Reservation(room=room, guest=guest, start=start, end=end, people=people, notes=notes,
                       daily_rate=room.daily_rate, status=status, created_by=actor)
    item.total = Decimal(item.nights) * item.daily_rate
    item.full_clean()
    validate_availability(room, start, end)
    item.save()
    audit(actor, "reserva.criada", item)
    return item


def locked_reservation(pk):
    """Ordem de bloqueio compartilhada: quarto, depois reserva. O quarto da reserva é imutável."""
    room_id = Reservation.objects.values_list("room_id", flat=True).get(pk=pk)
    room = Room.objects.select_for_update().get(pk=room_id)
    item = Reservation.objects.select_for_update().get(pk=pk)
    item.room = room
    return item


@transaction.atomic
def edit_reservation(pk, *, actor, start, end, people, notes, status):
    require_operator(actor)
    item = locked_reservation(pk)
    if not item.editable or status not in (Reservation.Status.PENDING, Reservation.Status.CONFIRMED):
        raise ValidationError("Somente reservas pendentes ou confirmadas podem ser editadas.")
    if start < timezone.localdate() and start != item.start:
        raise ValidationError("A nova entrada não pode estar no passado.")
    item.start, item.end, item.people, item.notes, item.status = start, end, people, notes, status
    item.total = Decimal(item.nights) * item.daily_rate - item.discount
    item.full_clean()
    if item.total < item.paid:
        raise ValidationError("O novo total não pode ser menor que o valor já recebido.")
    validate_availability(item.room, start, end, item.pk)
    item.save()
    audit(actor, "reserva.editada", item)
    return item


@transaction.atomic
def transition(pk, *, actor, action, reason=""):
    require_operator(actor)
    item = locked_reservation(pk)
    today = timezone.localdate()
    if action == "checkin":
        if item.status != Reservation.Status.CONFIRMED:
            raise ValidationError("Confirme a reserva antes de registrar a entrada.")
        if not item.start <= today < item.end:
            raise ValidationError("A entrada precisa ocorrer dentro do período reservado. Ajuste as datas, se necessário.")
        validate_availability(item.room, today, item.end, item.pk)
        item.status = Reservation.Status.IN_HOUSE
        item.checked_in_at = timezone.now()
    elif action == "checkout":
        if item.status != Reservation.Status.IN_HOUSE:
            raise ValidationError("A saída só pode ser registrada para um hóspede que está no hotel.")
        if item.balance > 0:
            raise ValidationError("Há valores pendentes. Registre o pagamento antes de concluir a saída.")
        item.status = Reservation.Status.FINISHED
        item.checked_out_at = timezone.now()
        item.room.status = Room.Status.CLEANING
        item.room.save(update_fields=["status"])
    elif action in ("cancel", "noshow"):
        if not item.editable:
            raise ValidationError("Esta reserva não pode mais ser cancelada ou marcada como ausência.")
        if not reason.strip():
            raise ValidationError("Informe o motivo para manter o histórico da operação.")
        if item.paid:
            raise ValidationError("A reserva possui recebimentos. Solicite ao administrador a conciliação antes do cancelamento; estornos não são suportados nesta versão.")
        if action == "noshow" and item.start > today:
            raise ValidationError("A data prevista de entrada ainda não chegou.")
        item.status = Reservation.Status.CANCELLED if action == "cancel" else Reservation.Status.NO_SHOW
        item.cancelled_by, item.cancelled_at, item.cancellation_reason = actor, timezone.now(), reason.strip()[:250]
    else:
        raise ValidationError("Operação inválida.")
    item.full_clean()
    item.save()
    audit(actor, f"reserva.{action}", item)
    return item


@transaction.atomic
def apply_discount(pk, *, actor, amount, reason):
    if not allowed(actor, ADMIN):
        raise PermissionDenied
    item = locked_reservation(pk)
    if item.status not in ACTIVE or not reason.strip():
        raise ValidationError("Informe a justificativa e selecione uma reserva ativa.")
    if amount < 0:
        raise ValidationError("O desconto não pode ser negativo.")
    item.discount = amount
    item.total = Decimal(item.nights) * item.daily_rate - amount
    item.full_clean()
    if item.total < item.paid:
        raise ValidationError("O desconto não pode reduzir o total abaixo do valor já recebido.")
    item.save()
    audit(actor, "reserva.desconto", item, amount=str(amount), reason=reason[:200])
    return item
