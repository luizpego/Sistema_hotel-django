import uuid
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


def reservation_code():
    return uuid.uuid4().hex[:12].upper()


class Reservation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        CONFIRMED = "confirmed", "Confirmada"
        IN_HOUSE = "in_house", "Hospedado"
        FINISHED = "finished", "Finalizada"
        CANCELLED = "cancelled", "Cancelada"
        NO_SHOW = "no_show", "Não compareceu"

    code = models.CharField("código", max_length=12, default=reservation_code, unique=True, editable=False)
    guest = models.ForeignKey("hospedes.Guest", verbose_name="hóspede", related_name="reservations", on_delete=models.PROTECT)
    room = models.ForeignKey("quartos.Room", verbose_name="quarto", related_name="reservations", on_delete=models.PROTECT)
    start = models.DateField("entrada")
    end = models.DateField("saída")
    people = models.PositiveSmallIntegerField("pessoas", validators=[MinValueValidator(1)])
    daily_rate = models.DecimalField("diária contratada", max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    discount = models.DecimalField("desconto autorizado", max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total = models.DecimalField("total contratado", max_digits=12, decimal_places=2)
    status = models.CharField("situação", max_length=20, choices=Status.choices, default=Status.CONFIRMED, db_index=True)
    notes = models.TextField("observações", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="reservations", on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="cancellations", null=True, blank=True, on_delete=models.PROTECT)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField("motivo", max_length=250, blank=True)

    class Meta:
        ordering = ["-start", "-pk"]
        verbose_name = "reserva"
        indexes = [models.Index(fields=["room", "start", "end"]), models.Index(fields=["status", "start"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(end__gt=models.F("start")), name="reservation_valid_dates"),
            models.CheckConstraint(condition=models.Q(people__gte=1), name="reservation_people_positive"),
            models.CheckConstraint(condition=models.Q(daily_rate__gt=0), name="reservation_rate_positive"),
            models.CheckConstraint(condition=models.Q(discount__gte=0) & models.Q(total__gte=0), name="reservation_money_nonnegative"),
            models.UniqueConstraint(fields=["room"], condition=models.Q(status="in_house"), name="one_stay_per_room"),
        ]

    @property
    def nights(self):
        return (self.end - self.start).days

    @property
    def paid(self):
        return self.payments.aggregate(value=models.Sum("amount"))["value"] or Decimal("0.00")

    @property
    def balance(self):
        return self.total - self.paid

    @property
    def editable(self):
        return self.status in (self.Status.PENDING, self.Status.CONFIRMED)

    def clean(self):
        errors = {}
        if self.start and self.end and self.end <= self.start:
            errors["end"] = "A saída precisa ser depois da entrada (pelo menos uma diária)."
        if self.room_id and self.people and self.people > self.room.capacity:
            errors["people"] = f"Este quarto comporta no máximo {self.room.capacity} pessoas."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.code} · {self.guest}"
