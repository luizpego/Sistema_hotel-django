from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from core.models import audit
from core.permissions import ADMIN, CLEANING, allowed
from .models import Room, RoomBlock


@transaction.atomic
def save_room(*, actor, data, pk=None):
    if not allowed(actor, ADMIN):
        raise PermissionDenied
    room = Room.objects.select_for_update().get(pk=pk) if pk else Room()
    for key in ("number", "category", "capacity", "daily_rate", "description", "status", "active"):
        setattr(room, key, data[key])
    if pk:
        stays = room.reservations.filter(status="in_house")
        if stays.exists() and (room.status != Room.Status.READY or not room.active):
            raise ValidationError("Registre a saída do hóspede antes de bloquear ou desativar este quarto.")
        if room.reservations.filter(status__in=["pending", "confirmed", "in_house"], end__gt=timezone.localdate(), people__gt=room.capacity).exists():
            raise ValidationError("A capacidade seria menor que o número de pessoas de uma reserva ativa.")
    room.full_clean()
    room.save()
    audit(actor, "quarto.salvo", room)
    return room


@transaction.atomic
def release_cleaning(pk, *, actor):
    if not allowed(actor, ADMIN, CLEANING):
        raise PermissionDenied
    room = Room.objects.select_for_update().get(pk=pk)
    if room.status != Room.Status.CLEANING:
        raise ValidationError("Este quarto não está na fila de limpeza.")
    if room.reservations.filter(status="in_house").exists():
        raise ValidationError("O quarto ainda possui uma hospedagem ativa.")
    room.status = Room.Status.READY
    room.save(update_fields=["status"])
    audit(actor, "quarto.limpeza_concluida", room)


@transaction.atomic
def block_room(pk, *, actor, start, end, reason):
    if not allowed(actor, ADMIN):
        raise PermissionDenied
    from reservas.services import conflicts
    room = Room.objects.select_for_update().get(pk=pk)
    block = RoomBlock(room=room, start=start, end=end, reason=reason, created_by=actor)
    block.full_clean()
    if conflicts(pk, start, end).exists():
        raise ValidationError("Existem reservas ativas nesse período. Resolva-as antes de bloquear.")
    if RoomBlock.objects.filter(room=room, active=True, start__lt=end, end__gt=start).exists():
        raise ValidationError("Já existe um bloqueio nesse período.")
    block.save()
    audit(actor, "quarto.bloqueado_periodo", block)
    return block


@transaction.atomic
def unblock(pk, *, actor):
    if not allowed(actor, ADMIN):
        raise PermissionDenied
    room_id = RoomBlock.objects.values_list("room_id", flat=True).get(pk=pk)
    Room.objects.select_for_update().get(pk=room_id)
    block = RoomBlock.objects.select_for_update().get(pk=pk)
    block.active = False
    block.save(update_fields=["active"])
    audit(actor, "quarto.bloqueio_removido", block)
