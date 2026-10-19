from django import forms
from core.forms import StyledFormMixin
from .models import Guest
from .validators import normalize_cpf


class GuestForm(StyledFormMixin, forms.ModelForm):
    cpf = forms.CharField(label="CPF", max_length=14, required=False,
                          help_text="Opcional. Aceita números ou o formato 000.000.000-00.")

    class Meta:
        model = Guest
        fields = ["name", "cpf", "phone", "email", "city", "state", "birth_date", "notes"]
        help_texts = {"cpf": "Opcional. Preencha apenas se necessário para a hospedagem.",
                      "notes": "Registre somente informações necessárias ao atendimento."}
        widgets = {"birth_date": forms.DateInput(format="%Y-%m-%d")}

    def clean_cpf(self):
        return normalize_cpf(self.cleaned_data.get("cpf")) or None
