from datetime import timedelta
from decimal import Decimal
from unittest import skipUnless
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import uuid
from django.core.exceptions import ValidationError
from django.db import connection, connections, IntegrityError, transaction
from django.test import TransactionTestCase
from django.utils import timezone
from core.testutils import HotelTestCase
from financeiro.services import record_payment
from hospedes.models import Guest
from quartos.models import Room
from quartos.services import block_room
from usuarios.models import User
from .models import Reservation
from .services import create_reservation, edit_reservation, transition, available_rooms


class ReservationTests(HotelTestCase):
    def test_valid_reservation_snapshot(self):
        item = self.book()
        self.assertEqual(item.total, Decimal("300.00"))
        self.room.daily_rate = Decimal("200.00")
        self.room.save()
        item.refresh_from_db()
        self.assertEqual(item.daily_rate, Decimal("150.00"))

    def test_overlaps_all_variations(self):
        self.book(start=self.today + timedelta(days=2), end=self.today + timedelta(days=5))
        for start, end in [(1, 3), (2, 5), (3, 4), (4, 6), (1, 6)]:
            with self.subTest(start=start, end=end), self.assertRaises(ValidationError):
                self.book(start=self.today + timedelta(days=start), end=self.today + timedelta(days=end))

    def test_same_day_turnover_allowed(self):
        self.book()
        self.book(start=self.today + timedelta(days=2), end=self.today + timedelta(days=3))
        self.assertEqual(Reservation.objects.count(), 2)

    def test_invalid_dates_and_capacity(self):
        for data in [{"end": self.today}, {"end": self.today - timedelta(days=1)}, {"start": self.today - timedelta(days=1)}, {"people": 3}, {"people": 0}]:
            with self.subTest(data=data), self.assertRaises(ValidationError):
                self.book(**data)

    def test_unready_room_rejected(self):
        for state in ["cleaning", "maintenance", "blocked"]:
            self.room.status = state
            self.room.save()
            with self.assertRaises(ValidationError):
                self.book()

    def test_cancel_releases_room_and_records_actor(self):
        item = self.book()
        transition(item.pk, actor=self.reception, action="cancel", reason="Mudança de planos")
        item.refresh_from_db()
        self.assertEqual(item.cancelled_by, self.reception)
        self.assertIsNotNone(item.cancelled_at)
        self.assertEqual(item.status, "cancelled")
        self.book()

    def test_checkin_checkout_requires_payment_and_marks_cleaning(self):
        item = self.book()
        transition(item.pk, actor=self.reception, action="checkin")
        with self.assertRaises(ValidationError):
            transition(item.pk, actor=self.reception, action="checkout")
        record_payment(item.pk, actor=self.reception, amount=item.total, method="pix", token=uuid.uuid4())
        transition(item.pk, actor=self.reception, action="checkout")
        item.refresh_from_db()
        self.room.refresh_from_db()
        self.assertEqual(item.status, "finished")
        self.assertIsNotNone(item.checked_out_at)
        self.assertEqual(self.room.status, "cleaning")

    def test_future_checkin_rejected(self):
        item = self.book(start=self.today + timedelta(days=1))
        with self.assertRaises(ValidationError):
            transition(item.pk, actor=self.reception, action="checkin")

    def test_repeated_checkin_rejected(self):
        item = self.book()
        transition(item.pk, actor=self.reception, action="checkin")
        with self.assertRaises(ValidationError):
            transition(item.pk, actor=self.reception, action="checkin")

    def test_pending_confirmation_edit_keeps_rate(self):
        item = self.book(status="pending")
        with self.assertRaises(ValidationError):
            transition(item.pk, actor=self.reception, action="checkin")
        self.room.daily_rate = Decimal("500")
        self.room.save()
        item = edit_reservation(item.pk, actor=self.reception, start=item.start, end=item.end + timedelta(days=1), people=1, notes="", status="confirmed")
        self.assertEqual(item.total, Decimal("450"))

    def test_no_show_requires_date_and_reason(self):
        item = self.book(start=self.today + timedelta(days=1))
        with self.assertRaises(ValidationError):
            transition(item.pk, actor=self.reception, action="noshow", reason="Ausente")
        item = self.book(end=self.today + timedelta(days=1))
        with self.assertRaises(ValidationError):
            transition(item.pk, actor=self.reception, action="cancel")
        transition(item.pk, actor=self.reception, action="noshow", reason="Sem contato")

    def test_reservation_views_persist_and_use_backend_validation(self):
        self.client.force_login(self.reception)
        data = {"room": self.room.pk, "guest": self.guest.pk, "start": str(self.today), "end": str(self.today + timedelta(days=2)), "people": 2, "status": "confirmed"}
        self.assertEqual(self.client.post("/reservas/nova/", data).status_code, 302)
        self.assertEqual(self.client.post("/reservas/nova/", data).status_code, 200)
        self.assertEqual(Reservation.objects.count(), 1)


class ConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.actor = User.objects.create_user("concorrencia", role="admin")
        self.guest = Guest.objects.create(name="Concorrência", phone="33999998888")
        self.room = Room.objects.create(number="201", category="double", capacity=2, daily_rate="100.00")
        self.today = timezone.localdate()

    def create(self):
        return create_reservation(actor=self.actor, guest=self.guest, room=self.room, start=self.today, end=self.today + timedelta(days=2), people=1)

    def race(self, operations):
        barrier = Barrier(2)
        def run(operation):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                operation()
                return "ok"
            except ValidationError:
                return "rejected"
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(run, operations))

    def test_simultaneous_reservations_only_one_succeeds(self):
        results = self.race([self.create, self.create])
        self.assertCountEqual(results, ["ok", "rejected"])
        self.assertEqual(Reservation.objects.count(), 1)

    def test_simultaneous_payments_do_not_overpay(self):
        item = self.create()
        def pay():
            record_payment(item.pk, actor=self.actor, amount=Decimal("150"), method="pix", token=uuid.uuid4())
        self.assertCountEqual(self.race([pay, pay]), ["ok", "rejected"])
        self.assertEqual(item.paid, Decimal("150"))

    def test_simultaneous_block_and_reservation_only_one_succeeds(self):
        def block():
            block_room(self.room.pk, actor=self.actor, start=self.today, end=self.today + timedelta(days=1), reason="Manutenção")
        self.assertCountEqual(self.race([block, self.create]), ["ok", "rejected"])

    @skipUnless(connection.vendor == "postgresql", "Restrição específica do PostgreSQL; executada no job PostgreSQL da CI.")
    def test_database_rejects_raw_overlapping_insert(self):
        item = self.create()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Reservation.objects.create(guest=self.guest, room=self.room, start=item.start, end=item.end,
                                       people=1, daily_rate=100, total=200, created_by=self.actor)
