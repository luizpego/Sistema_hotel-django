from datetime import timedelta
from django.core.exceptions import ValidationError
from core.testutils import HotelTestCase
from .forms import GuestForm
from .models import Guest


class GuestTests(HotelTestCase):
    def test_form_accepts_formatted_cpf(self):
        form = GuestForm(data={"name": "Outra Pessoa", "phone": "(33) 99999-2222", "cpf": "111.444.777-35"})
        self.assertTrue(form.is_valid(), form.errors)
        item = form.save()
        self.assertEqual(item.cpf, "11144477735")
        self.assertEqual(item.phone, "33999992222")

    def test_invalid_cpf(self):
        for cpf in ["11111111111", "12345678900", "5299822472x"]:
            with self.subTest(cpf=cpf), self.assertRaises(ValidationError):
                Guest.objects.create(name="Outro", phone="33999992222", cpf=cpf)

    def test_cpf_unique(self):
        with self.assertRaises(ValidationError):
            Guest.objects.create(name="Outro", phone="33999992222", cpf=self.guest.cpf)

    def test_name_phone_prevent_duplicate(self):
        with self.assertRaises(ValidationError):
            Guest.objects.create(name="  MARIA   DE TESTE ", phone="(33) 99999-1111")

    def test_blank_cpf_allowed_multiple_times(self):
        for i in range(2):
            Guest.objects.create(name=f"Sem CPF {i}", phone=f"3399999333{i}")
        self.assertEqual(Guest.objects.filter(cpf__isnull=True).count(), 2)

    def test_future_birth_rejected(self):
        self.guest.birth_date = self.today + timedelta(days=1)
        with self.assertRaises(ValidationError):
            self.guest.save()

    def test_list_masks_cpf_and_escapes_name(self):
        self.client.force_login(self.reception)
        self.guest.name = "<script>alert(1)</script>"
        self.guest.save()
        response = self.client.get("/hospedes/")
        self.assertNotContains(response, self.guest.cpf)
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "<script>alert")

    def test_guest_create_and_edit_views(self):
        self.client.force_login(self.reception)
        response = self.client.post("/hospedes/novo/", {"name": "João Silva", "phone": "33988887777"})
        self.assertEqual(response.status_code, 302)
        item = Guest.objects.get(name="João Silva")
        response = self.client.post(f"/hospedes/{item.pk}/editar/", {"name": "João da Silva", "phone": item.phone})
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.name, "João da Silva")
