from django.urls import path
from . import views

app_name = "relatorios"
urlpatterns = [path("", views.index, name="index"), path("exportar/<str:kind>/", views.export, name="export"),
               path("modelo/<str:kind>/", views.template, name="template"), path("importar/", views.import_file, name="import"),
               path("importar/confirmar/", views.confirm_import, name="confirm")]
