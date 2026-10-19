from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class Room(models.Model):
    class Status(models.TextChoices):
        READY = "ready", "Disponível para uso"
        CLEANING = "cleaning", "Em limpeza"
        MAINTENANCE = "maintenance", "Em manutenção"
        BLOCKED = "blocked", "Bloqueado"

    class Category(models.TextChoices):
        SINGLE = "single", "Solteiro"
        DOUBLE = "double", "Casal"
        TWIN = "twin", "Duplo"
        FAMILY = "family", "Família"
        SUITE = "suite", "Suíte"

    number = models.CharField("número", max_length=12, unique=True)
    category = models.CharField("categoria", max_length=20, choices=Category.choices)
    capacity = models.PositiveSmallIntegerField("capacidade", validators=[MinValueValidator(1)])
    daily_rate = models.DecimalField("diária padrão", max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    description = models.TextField("descrição", blank=True)
    status = models.CharField("situação operacional", max_length=20, choices=Status.choices, default=Status.READY, db_index=True)
    active = models.BooleanField("ativo", default=True)

    class Meta:
        ordering = ["number"]
        verbose_name = "quarto"
        constraints = [
            models.CheckConstraint(condition=models.Q(capacity__gte=1), name="room_capacity_positive"),
            models.CheckConstraint(condition=models.Q(daily_rate__gt=0), name="room_rate_positive"),
        ]

    def __str__(self):
        return f"Quarto {self.number} · {self.get_category_display()}"


class RoomBlock(models.Model):
    room = models.ForeignKey(Room, related_name="blocks", on_delete=models.PROTECT)
    start = models.DateField("início")
    end = models.DateField("liberação (data exclusiva)")
    reason = models.CharField("motivo", max_length=200)
    created_by = models.ForeignKey("usuarios.User", on_delete=models.PROTECT)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["start"]
        constraints = [models.CheckConstraint(condition=models.Q(end__gt=models.F("start")), name="block_valid_period")]
        indexes = [models.Index(fields=["room", "start", "end"])]

    def clean(self):
        if self.start and self.end and self.end <= self.start:
            raise ValidationError("A liberação precisa ser posterior ao início do bloqueio.")
