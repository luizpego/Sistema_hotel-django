from django.urls import path
from . import views

app_name = "financeiro"
urlpatterns = [path("", views.summary, name="summary"), path("reserva/<int:pk>/receber/", views.payment_create, name="payment")]
