from django import forms
from core.forms import StyledFormMixin


class ImportForm(StyledFormMixin, forms.Form):
    kind = forms.ChoiceField(label="O que deseja importar?", choices=[("guests", "Hóspedes"), ("rooms", "Quartos")])
    file = forms.FileField(label="Planilha .xlsx", help_text="Até 2 MB e 1.000 linhas. Utilize o modelo disponível nesta página.", widget=forms.FileInput(attrs={"accept": ".xlsx"}))

    def clean_file(self):
        file = self.cleaned_data["file"]
        if not file.name.lower().endswith(".xlsx") or file.size > 2 * 1024 * 1024:
            raise forms.ValidationError("Envie um arquivo .xlsx de até 2 MB.")
        return file
