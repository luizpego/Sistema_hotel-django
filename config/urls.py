from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("conta/", include("usuarios.urls")),
    path("hospedes/", include("hospedes.urls")),
    path("quartos/", include("quartos.urls")),
    path("reservas/", include("reservas.urls")),
    path("financeiro/", include("financeiro.urls")),
    path("relatorios/", include("relatorios.urls")),
    path("", include("core.urls")),
]
handler403 = "core.views.forbidden"
handler404 = "core.views.not_found"
handler500 = "core.views.server_error"
