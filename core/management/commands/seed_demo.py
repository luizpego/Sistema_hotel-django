from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from hospedes.models import Guest
from quartos.models import Room
from reservas.models import Reservation
from reservas.services import create_reservation, transition
from usuarios.models import User


class Command(BaseCommand):
    help = "Adiciona quartos e hóspedes fictícios para demonstração local, sem criar senhas."

    def add_arguments(self, parser):
        parser.add_argument("--with-reservations", action="store_true", help="Cria reservas de demonstração usando o primeiro administrador.")

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("O comando de demonstração só está disponível com DEBUG=true.")
        if Room.objects.exists() or Guest.objects.exists():
            raise CommandError("Use uma base vazia para a demonstração. Nenhum dado existente foi alterado.")
        rooms = []
        for number in range(101, 113):
            category = "suite" if number >= 110 else ("double" if number % 2 else "twin")
            room = Room(number=str(number), category=category, capacity=2 if number < 110 else 4,
                        daily_rate=Decimal("180.00") if number < 110 else Decimal("260.00"),
                        status=Room.Status.CLEANING if number in (105, 108) else Room.Status.READY)
            room.full_clean()
            room.save()
            rooms.append(room)
        guests = [Guest.objects.create(name=name, phone=f"3399999000{i}", city="São João Evangelista", state="MG")
                  for i, name in enumerate(["Mariana Costa (Demonstração)", "Pedro Almeida (Demonstração)", "Ana Souza (Demonstração)", "Carlos Lima (Demonstração)"])]
        if options["with_reservations"]:
            actor = User.objects.filter(is_active=True).filter(role="admin").first() or User.objects.filter(is_superuser=True, is_active=True).first()
            if not actor:
                raise CommandError("Crie um administrador com createsuperuser antes de gerar reservas.")
            today = timezone.localdate()
            for index, guest in enumerate(guests):
                item = create_reservation(actor=actor, room=rooms[index], guest=guest, start=today,
                                          end=today + timedelta(days=1 if index == 0 else 3), people=2)
                if index < 2:
                    transition(item.pk, actor=actor, action="checkin")
        self.stdout.write(self.style.SUCCESS("Demonstração criada: 12 quartos e 4 hóspedes fictícios. Nenhuma credencial foi criada."))
