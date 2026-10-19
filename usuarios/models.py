from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrador"
        RECEPTION = "reception", "Recepcionista"
        CLEANING = "cleaning", "Limpeza"

    role = models.CharField("perfil", max_length=20, choices=Role.choices, default=Role.RECEPTION)

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.ADMIN
            self.is_staff = True
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.get_full_name() or self.username


class LoginAttempt(models.Model):
    """Contador persistente sem armazenar IP ou nome de usuário em texto aberto."""
    key = models.CharField(max_length=64, unique=True)
    count = models.PositiveIntegerField(default=0)
    last_at = models.DateTimeField()
