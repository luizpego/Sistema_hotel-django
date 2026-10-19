from django import forms


class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            css = "form-check-input" if isinstance(widget, forms.CheckboxInput) else (
                "form-select" if isinstance(widget, forms.Select) else "form-control")
            widget.attrs.setdefault("class", css)
            if field.help_text:
                widget.attrs["aria-describedby"] = f"id_{name}_helptext"
            if isinstance(widget, forms.DateInput):
                widget.input_type = "date"
                widget.format = "%Y-%m-%d"
            if isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("rows", 3)


class PeriodForm(StyledFormMixin, forms.Form):
    start = forms.DateField(label="De", widget=forms.DateInput(format="%Y-%m-%d"), required=False)
    end = forms.DateField(label="Até", widget=forms.DateInput(format="%Y-%m-%d"), required=False)

    def clean(self):
        data = super().clean()
        if data.get("start") and data.get("end") and data["end"] < data["start"]:
            raise forms.ValidationError("A data final precisa ser igual ou posterior à inicial.")
        return data
