from django.core.exceptions import ValidationError
from django.db import transaction
from core.models import audit
from reservas.services import ACTIVE, locked_reservation, require_operator
from .models import Payment


@transaction.atomic
def record_payment(pk, *, actor, amount, method, token, notes=""):
    require_operator(actor)
    item = locked_reservation(pk)
    existing = Payment.objects.filter(token=token).first()
    if existing:
        if existing.reservation_id != item.pk or existing.amount != amount or existing.method != method:
            raise ValidationError("Este formulário já foi utilizado. Abra um novo registro de pagamento.")
        return existing
    if item.status not in ACTIVE:
        raise ValidationError("Somente reservas ativas podem receber pagamentos.")
    if amount > item.balance:
        raise ValidationError("O pagamento não pode ser maior que o saldo pendente.")
    payment = Payment(reservation=item, amount=amount, method=method, token=token, notes=notes, received_by=actor)
    payment.full_clean()
    payment.save()
    audit(actor, "pagamento.registrado", payment, amount=str(amount))
    return payment
