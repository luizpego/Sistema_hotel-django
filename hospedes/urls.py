from django.urls import path
from . import views

app_name = "hospedes"
urlpatterns = [path("", views.guest_list, name="list"), path("novo/", views.guest_edit, name="create"),
               path("<int:pk>/", views.guest_detail, name="detail"), path("<int:pk>/editar/", views.guest_edit, name="edit")]
