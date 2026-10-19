from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.crypto import salted_hmac
from core.models import audit
from core.permissions import ADMIN, roles_required
from .forms import EmployeeForm, LoginForm
from .models import LoginAttempt, User


class HotelLoginView(LoginView):
    template_name = "usuarios/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def post(self, request, *args, **kwargs):
        key = salted_hmac("hotel-login", request.POST.get("username", "").strip().casefold()).hexdigest()
        now = timezone.now()
        with transaction.atomic():
            attempt, _ = LoginAttempt.objects.select_for_update().get_or_create(key=key, defaults={"last_at": now})
            if attempt.last_at < now - timedelta(minutes=15):
                attempt.count = 0
            if attempt.count >= 8:
                form = self.get_form()
                form.add_error(None, "Muitas tentativas. Aguarde 15 minutos e tente novamente.")
                return self.render_to_response(self.get_context_data(form=form), status=429)
            attempt.count += 1
            attempt.last_at = now
            attempt.save()
        response = super().post(request, *args, **kwargs)
        if request.user.is_authenticated:
            LoginAttempt.objects.filter(key=key).delete()
            audit(request.user, "usuario.login", request.user)
        return response


@roles_required(ADMIN)
def employees(request):
    return render(request, "usuarios/list.html", {"employees": User.objects.order_by("first_name", "username")})


@roles_required(ADMIN)
def employee_edit(request, pk=None):
    item = get_object_or_404(User, pk=pk) if pk else None
    form = EmployeeForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                # Serializa alterações de perfil, inclusive desativações simultâneas.
                list(User.objects.select_for_update().order_by("pk"))
                saved = form.save(commit=False)
                if item and item.is_superuser:
                    raise ValidationError("Superusuários devem ser gerenciados pelo responsável técnico.")
                if saved.pk == request.user.pk and (not saved.is_active or saved.role != ADMIN):
                    raise ValidationError("Você não pode remover seu próprio acesso de administrador.")
                if form.cleaned_data["password"]:
                    saved.set_password(form.cleaned_data["password"])
                saved.is_staff = saved.role == ADMIN
                saved.save()
                audit(request.user, "usuario.salvo", saved)
            messages.success(request, "Funcionário salvo com sucesso.")
            return redirect("usuarios:list")
        except ValidationError as error:
            form.add_error(None, error)
    return render(request, "core/form.html", {"form": form, "title": "Editar funcionário" if pk else "Novo funcionário", "back_url": "usuarios:list"})
