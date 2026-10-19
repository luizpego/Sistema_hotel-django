from datetime import timedelta
from django.core.exceptions import ValidationError, PermissionDenied
from core.testutils import HotelTestCase
from reservas.services import available_rooms, transition
from .models import Room
from .services import block_room, release_cleaning, save_room, unblock


class RoomTests(HotelTestCase):
    def test_room_create_view_and_unique_number(self):
        self.client.force_login(self.admin)
        data = {"number": "102", "category": "single", "capacity": 1, "daily_rate": "100.00", "status": "ready", "active": "on"}
        self.assertEqual(self.client.post("/quartos/novo/", data).status_code, 302)
        response = self.client.post("/quartos/novo/", data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Room.objects.filter(number="102").count(), 1)

    def test_invalid_room_values(self):
        for field in ("capacity", "daily_rate"):
            setattr(self.room, field, 0)
            with self.assertRaises(ValidationError):
                self.room.full_clean()
            self.room.refresh_from_db()

    def test_block_excludes_period_only(self):
        start, end = self.today + timedelta(days=4), self.today + timedelta(days=7)
        item = block_room(self.room.pk, actor=self.admin, start=start, end=end, reason="Pintura")
        self.assertFalse(available_rooms(start, end).exists())
        self.assertTrue(available_rooms(end, end + timedelta(days=1)).exists())
        unblock(item.pk, actor=self.admin)
        self.assertTrue(available_rooms(start, end).exists())

    def test_block_cannot_conflict_with_reservation(self):
        self.book()
        with self.assertRaises(ValidationError):
            block_room(self.room.pk, actor=self.admin, start=self.today, end=self.today + timedelta(days=1), reason="Obra")

    def test_cleaner_releases_and_audits(self):
        self.room.status = Room.Status.CLEANING
        self.room.save()
        release_cleaning(self.room.pk, actor=self.cleaner)
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, Room.Status.READY)
        with self.assertRaises(ValidationError):
            release_cleaning(self.room.pk, actor=self.cleaner)

    def test_reception_cannot_release_cleaning(self):
        with self.assertRaises(PermissionDenied):
            release_cleaning(self.room.pk, actor=self.reception)

    def test_cannot_block_occupied_or_reduce_capacity(self):
        item = self.book()
        transition(item.pk, actor=self.reception, action="checkin")
        data = {key: getattr(self.room, key) for key in ["number", "category", "capacity", "daily_rate", "description", "status", "active"]}
        data["status"] = "maintenance"
        with self.assertRaises(ValidationError):
            save_room(actor=self.admin, pk=self.room.pk, data=data)
        data["status"], data["capacity"] = "ready", 1
        with self.assertRaises(ValidationError):
            save_room(actor=self.admin, pk=self.room.pk, data=data)
