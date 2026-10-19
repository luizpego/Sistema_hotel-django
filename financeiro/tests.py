from decimal import Decimal
import uuid
from django.core.exceptions import ValidationError, PermissionDenied
from core.testutils import HotelTestCase
from reservas.services import apply_discount, transition
from .models import Payment
from .services import record_payment


class FinanceTests(HotelTestCase):
    def pay(self, item, amount, token=None, actor=None):
        return record_payment(item.pk, actor=actor or self.reception, amount=Decimal(amount), method="pix", token=token or uuid.uuid4())

    def test_partial_and_multiple_payments(self):
        item = self.book()
        self.pay(item, "100.10")
        self.pay(item, "50.20")
        self.assertEqual(item.balance, Decimal("149.70"))

    def test_invalid_payment_values(self):
        item = self.book()
        for amount in ["0", "-1", "300.01"]:
            with self.subTest(amount=amount), self.assertRaises(ValidationError):
                self.pay(item, amount)
        self.assertFalse(Payment.objects.exists())

    def test_payment_idempotency(self):
        item = self.book()
        token = uuid.uuid4()
        first, second = self.pay(item, "100", token), self.pay(item, "100", token)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(item.payments.count(), 1)

    def test_idempotency_token_cannot_be_reused_with_new_values(self):
        item = self.book()
        token = uuid.uuid4()
        self.pay(item, "100", token)
        with self.assertRaises(ValidationError):
            self.pay(item, "150", token)

    def test_discount_permission_and_minimum_total(self):
        item = self.book()
        with self.assertRaises(PermissionDenied):
            apply_discount(item.pk, actor=self.reception, amount=Decimal("20"), reason="Autorizado")
        apply_discount(item.pk, actor=self.admin, amount=Decimal("20"), reason="Cortesia")
        item.refresh_from_db()
        self.assertEqual(item.total, Decimal("280"))
        self.pay(item, "250")
        with self.assertRaises(ValidationError):
            apply_discount(item.pk, actor=self.admin, amount=Decimal("100"), reason="Excesso")

    def test_cancel_with_payment_does_not_hide_receipts(self):
        item = self.book()
        self.pay(item, "100")
        with self.assertRaises(ValidationError):
            transition(item.pk, actor=self.reception, action="cancel", reason="Pedido")
        self.assertEqual(item.payments.count(), 1)

    def test_payment_view(self):
        item = self.book()
        self.client.force_login(self.reception)
        data = {"amount": "100.00", "method": "pix", "token": str(uuid.uuid4())}
        self.assertEqual(self.client.post(f"/financeiro/reserva/{item.pk}/receber/", data).status_code, 302)
        self.assertEqual(item.paid, Decimal("100"))
