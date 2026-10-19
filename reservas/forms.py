from django import forms
from django.utils import timezone
from core.forms import StyledFormMixin
from hospedes.models import Guest
from quartos.models import Room
from .models import Reservation
from .services import available_rooms


class AvailabilityForm(StyledFormMixin, forms.Form):
    start = forms.DateField(label="Entrada", widget=forms.DateInput(format="%Y-%m-%d"))
    end = forms.DateField(label="Saída", widget=forms.DateInput(format="%Y-%m-%d"))
    category = forms.ChoiceField(label="Categoria", required=False, choices=[("", "Todas as categorias"), *Room.Category.choices])

    def clean(self):
        data = super().clean()
        if data.get("start") and data["start"] < timezone.localdate():
            self.add_error("start", "Escolha hoje ou uma data futura.")
        if data.get("start") and data.get("end") and data["end"] <= data["start"]:
            self.add_error("end", "A saída precisa ser depois da entrada.")
        return data


class ReservationForm(StyledFormMixin, forms.Form):
    start = forms.DateField(label="Entrada", widget=forms.DateInput(format="%Y-%m-%d"))
    end = forms.DateField(label="Saída", widget=forms.DateInput(format="%Y-%m-%d"))
    room = forms.ModelChoiceField(label="Quarto", queryset=Room.objects.none())
    guest = forms.ModelChoiceField(label="Hóspede responsável", queryset=Guest.objects.all())
    people = forms.IntegerField(label="Quantidade de pessoas", min_value=1, initial=1)
    status = forms.ChoiceField(label="Situação", choices=[(Reservation.Status.CONFIRMED, "Confirmada"), (Reservation.Status.PENDING, "Pendente")])
    notes = forms.CharField(label="Observações", required=False, widget=forms.Textarea)

    def __init__(self, *args, instance=None, **kwargs):
        self.instance = instance
        super().__init__(*args, **kwargs)
        if instance:
            self.initial.update({name: getattr(instance, name) for name in ("start", "end", "people", "status", "notes")})
            self.fields.pop("room")
            self.fields.pop("guest")
        else:
            source = self.data if self.is_bound else self.initial
            try:
                start = forms.DateField().clean(source.get("start"))
                end = forms.DateField().clean(source.get("end"))
                self.fields["room"].queryset = available_rooms(start, end)
            except (forms.ValidationError, TypeError, ValueError):
                pass


class ReasonForm(StyledFormMixin, forms.Form):
    reason = forms.CharField(label="Motivo", max_length=250, widget=forms.Textarea)


class DiscountForm(StyledFormMixin, forms.Form):
    amount = forms.DecimalField(label="Desconto total autorizado", max_digits=10, decimal_places=2, min_value=0)
    reason = forms.CharField(label="Justificativa", max_length=200, widget=forms.Textarea)
