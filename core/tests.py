from django.test import Client
from django.urls import reverse
from core.testutils import HotelTestCase
from .models import AuditEvent


class SecurityAndPagesTests(HotelTestCase):
    def test_login_logout_and_rate_limit(self):
        for _ in range(8):
            response = self.client.post(reverse("usuarios:login"), {"username": "gestao", "password": "errada"})
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.post(reverse("usuarios:login"), {"username": "gestao", "password": "errada"}).status_code, 429)
        response = self.client.post(reverse("usuarios:login"), {"username": "recepcao", "password": "Hotel-Teste-73!"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(AuditEvent.objects.filter(action="usuario.login").exists())
        self.assertEqual(self.client.get(reverse("usuarios:logout")).status_code, 405)
        self.assertEqual(self.client.post(reverse("usuarios:logout")).status_code, 302)

    def test_cleaner_cannot_see_personal_or_financial_data(self):
        item = self.book()
        self.client.force_login(self.cleaner)
        for url in ["/hospedes/", f"/hospedes/{self.guest.pk}/", "/reservas/", f"/reservas/{item.pk}/", "/financeiro/", "/relatorios/", "/quartos/", "/conta/funcionarios/"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)
        response = self.client.get("/quartos/limpeza/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.guest.name)
        self.assertRedirects(self.client.get("/"), "/quartos/limpeza/")

    def test_reception_backend_permissions(self):
        item = self.book()
        self.client.force_login(self.reception)
        for url in ["/financeiro/", "/quartos/novo/", f"/quartos/{self.room.pk}/editar/", "/conta/funcionarios/", f"/reservas/{item.pk}/desconto/", "/relatorios/exportar/payments/", "/relatorios/exportar/financial/"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)
                self.assertEqual(self.client.post(url, {}).status_code, 403)
        self.assertEqual(self.client.post("/relatorios/importar/", {"kind": "rooms"}).status_code, 200)

    def test_anonymous_requires_login(self):
        for url in ["/", "/quartos/", "/hospedes/", "/reservas/", "/relatorios/", "/financeiro/"]:
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_csrf_is_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.reception)
        self.assertEqual(client.post("/hospedes/novo/", {"name": "Inválido", "phone": "33999998888"}).status_code, 403)

    def test_pages_render_for_administrator(self):
        item = self.book()
        self.client.force_login(self.admin)
        urls = ["/", "/hospedes/", "/hospedes/novo/", f"/hospedes/{self.guest.pk}/", f"/hospedes/{self.guest.pk}/editar/",
                "/quartos/", "/quartos/novo/", f"/quartos/{self.room.pk}/", f"/quartos/{self.room.pk}/editar/", "/quartos/limpeza/",
                f"/quartos/{self.room.pk}/bloquear/", "/reservas/", "/reservas/disponibilidade/", f"/reservas/{item.pk}/",
                f"/reservas/{item.pk}/editar/", f"/reservas/{item.pk}/checkin/", f"/reservas/{item.pk}/cancel/", f"/reservas/{item.pk}/desconto/",
                f"/financeiro/reserva/{item.pk}/receber/", "/financeiro/", "/relatorios/", "/relatorios/importar/", "/conta/funcionarios/", "/conta/funcionarios/novo/", "/conta/senha/"]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        self.assertContains(self.client.get("/"), "R$ 0,00")

    def test_privacy_headers(self):
        self.client.force_login(self.reception)
        response = self.client.get("/hospedes/")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("frame-ancestors 'none'", response["Content-Security-Policy"])

    def test_staff_create_and_prevent_self_demotion(self):
        self.client.force_login(self.admin)
        data = {"username": "nova_limp", "first_name": "Lúcia", "role": "cleaning", "is_active": "on", "password": "Nova-Senha-93!"}
        self.assertEqual(self.client.post("/conta/funcionarios/novo/", data).status_code, 302)
        data = {"username": self.admin.username, "role": "reception", "is_active": "on"}
        self.assertEqual(self.client.post(f"/conta/funcionarios/{self.admin.pk}/", data).status_code, 200)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, "admin")

    def test_invalid_report_dates_do_not_export(self):
        self.client.force_login(self.admin)
        response = self.client.get("/relatorios/exportar/payments/?start=2026-12-20&end=2026-01-01")
        self.assertEqual(response.status_code, 302)
