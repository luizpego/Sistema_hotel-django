import uuid
from decimal import Decimal
from django import forms
from core.forms import StyledFormMixin
from .models import Payment


class PaymentForm(StyledFormMixin, forms.Form):
    amount = forms.DecimalField(label="Valor recebido", max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    method = forms.ChoiceField(label="Forma de pagamento", choices=Payment.Method.choices)
    notes = forms.CharField(label="Observação", max_length=200, required=False)
    token = forms.UUIDField(widget=forms.HiddenInput, initial=uuid.uuid4)
