from django import forms
from core.forms import StyledFormMixin
from .models import Room, RoomBlock


class RoomForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Room
        fields = ["number", "category", "capacity", "daily_rate", "description", "status", "active"]


class BlockForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = RoomBlock
        fields = ["start", "end", "reason"]
        widgets = {"start": forms.DateInput(format="%Y-%m-%d"), "end": forms.DateInput(format="%Y-%m-%d")}
