from django.urls import path
from . import views

app_name = "reservas"
urlpatterns = [path("", views.reservation_list, name="list"), path("disponibilidade/", views.availability, name="availability"),
               path("nova/", views.reservation_edit, name="create"), path("<int:pk>/", views.reservation_detail, name="detail"),
               path("<int:pk>/editar/", views.reservation_edit, name="edit"), path("<int:pk>/desconto/", views.discount, name="discount"),
               path("<int:pk>/<str:action>/", views.action, name="action")]
