from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.password_validation import validate_password
from core.forms import StyledFormMixin
from .models import User


class LoginForm(StyledFormMixin, AuthenticationForm):
    username = forms.CharField(label="Usuário", widget=forms.TextInput(attrs={"autocomplete": "username", "autofocus": True}))
    password = forms.CharField(label="Senha", widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))


class ChangePasswordForm(StyledFormMixin, PasswordChangeForm):
    pass


class EmployeeForm(StyledFormMixin, forms.ModelForm):
    password = forms.CharField(label="Nova senha", required=False, widget=forms.PasswordInput,
                               help_text="Obrigatória no cadastro. Na edição, deixe em branco para manter a senha.")

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "role", "is_active"]

    def clean_password(self):
        value = self.cleaned_data.get("password")
        if not self.instance.pk and not value:
            raise forms.ValidationError("Defina uma senha inicial para o funcionário.")
        if value:
            candidate = User(username=self.cleaned_data.get("username", ""), email=self.cleaned_data.get("email", ""),
                             first_name=self.cleaned_data.get("first_name", ""), last_name=self.cleaned_data.get("last_name", ""))
            validate_password(value, candidate)
        return value
