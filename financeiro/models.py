import uuid
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "Dinheiro"
        PIX = "pix", "Pix"
        CREDIT = "credit", "Cartão de crédito"
        DEBIT = "debit", "Cartão de débito"
        TRANSFER = "transfer", "Transferência bancária"

    reservation = models.ForeignKey("reservas.Reservation", related_name="payments", on_delete=models.PROTECT)
    amount = models.DecimalField("valor recebido", max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    method = models.CharField("forma de pagamento", max_length=20, choices=Method.choices)
    received_at = models.DateTimeField("recebido em", auto_now_add=True, db_index=True)
    received_by = models.ForeignKey("usuarios.User", on_delete=models.PROTECT)
    notes = models.CharField("observação", max_length=200, blank=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        ordering = ["-received_at"]
        verbose_name = "pagamento"
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name="payment_positive")]
