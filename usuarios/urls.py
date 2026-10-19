from django.contrib.auth import views as auth_views
from django.urls import path
from . import views
from .forms import ChangePasswordForm

app_name = "usuarios"
urlpatterns = [
    path("entrar/", views.HotelLoginView.as_view(), name="login"),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
    path("senha/", auth_views.PasswordChangeView.as_view(form_class=ChangePasswordForm, template_name="usuarios/password.html", success_url="/"), name="password"),
    path("funcionarios/", views.employees, name="list"),
    path("funcionarios/novo/", views.employee_edit, name="create"),
    path("funcionarios/<int:pk>/", views.employee_edit, name="edit"),
]
