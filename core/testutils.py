from datetime import timedelta
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from hospedes.models import Guest
from quartos.models import Room
from reservas.services import create_reservation
from usuarios.models import User


class HotelTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user("gestao", password="Hotel-Teste-73!", role="admin")
        cls.reception = User.objects.create_user("recepcao", password="Hotel-Teste-73!", role="reception")
        cls.cleaner = User.objects.create_user("limpeza", password="Hotel-Teste-73!", role="cleaning")
        cls.guest = Guest.objects.create(name="Maria de Teste", phone="33999991111", cpf="52998224725")
        cls.room = Room.objects.create(number="101", category="double", capacity=2, daily_rate=Decimal("150.00"))
        cls.today = timezone.localdate()

    def book(self, **kwargs):
        data = {"actor": self.reception, "room": self.room, "guest": self.guest,
                "start": self.today, "end": self.today + timedelta(days=2), "people": 2}
        data.update(kwargs)
        return create_reservation(**data)
