from django.urls import path
from . import views

app_name = "quartos"
urlpatterns = [path("", views.room_list, name="list"), path("novo/", views.room_edit, name="create"),
               path("limpeza/", views.cleaning, name="cleaning"), path("<int:pk>/", views.room_detail, name="detail"),
               path("<int:pk>/editar/", views.room_edit, name="edit"), path("<int:pk>/liberar/", views.release, name="release"),
               path("<int:pk>/bloquear/", views.block, name="block"), path("bloqueios/<int:pk>/remover/", views.unblock, name="unblock")]
