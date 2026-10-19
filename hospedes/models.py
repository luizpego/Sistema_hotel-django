import re
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from .validators import normalize_cpf, validate_cpf

STATES = [(s, s) for s in "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()]


class Guest(models.Model):
    name = models.CharField("nome completo", max_length=160)
    cpf = models.CharField("CPF", max_length=11, unique=True, blank=True, null=True, validators=[validate_cpf])
    phone = models.CharField("telefone", max_length=25)
    email = models.EmailField("e-mail", blank=True)
    birth_date = models.DateField("data de nascimento", blank=True, null=True)
    city = models.CharField("cidade", max_length=100, blank=True)
    state = models.CharField("estado", max_length=2, choices=STATES, blank=True)
    notes = models.TextField("observações", blank=True)
    identity_key = models.CharField(max_length=220, unique=True, editable=False, blank=True)
    created_at = models.DateTimeField("cadastro", auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["name"]), models.Index(fields=["phone"])]
        verbose_name = "hóspede"

    def clean(self):
        self.name = " ".join(self.name.split())
        self.cpf = normalize_cpf(self.cpf) or None
        validate_cpf(self.cpf)
        if self.birth_date and self.birth_date > timezone.localdate():
            raise ValidationError({"birth_date": "A data de nascimento não pode estar no futuro."})
        digits = re.sub(r"\D", "", self.phone)
        if not 8 <= len(digits) <= 15:
            raise ValidationError({"phone": "Informe um telefone com DDD (8 a 15 dígitos)."})
        self.phone = digits
        self.identity_key = f"{self.name.casefold()}|{digits}"
        if Guest.objects.filter(identity_key=self.identity_key).exclude(pk=self.pk).exists():
            raise ValidationError("Já existe um hóspede com este nome e telefone. Utilize o cadastro existente.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def masked_cpf(self):
        return f"***.***.{self.cpf[6:9]}-**" if self.cpf else "Não informado"

    def __str__(self):
        return self.name
