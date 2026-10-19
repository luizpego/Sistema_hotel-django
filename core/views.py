from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from core.permissions import ADMIN, CLEANING, RECEPTION, allowed
from financeiro.models import Payment
from quartos.models import Room
from reservas.models import Reservation


@login_required
def dashboard(request):
    if allowed(request.user, CLEANING) and not allowed(request.user, ADMIN, RECEPTION):
        return redirect("quartos:cleaning")
    if not allowed(request.user, ADMIN, RECEPTION):
        return forbidden(request, None)
    today = timezone.localdate()
    rooms = list(Room.objects.filter(active=True))
    stays = {r.room_id: r for r in Reservation.objects.filter(status=Reservation.Status.IN_HOUSE).select_related("guest")}
    arrivals = Reservation.objects.filter(start=today, status__in=["pending", "confirmed"]).select_related("guest", "room")
    departures = Reservation.objects.filter(status="in_house", end__lte=today).select_related("guest", "room")
    from reservas.services import available_rooms
    from datetime import timedelta
    free_ids = set(available_rooms(today, today + timedelta(days=1)).values_list("pk", flat=True))
    for room in rooms:
        room.stay = stays.get(room.pk)
        room.free_today = room.pk in free_ids
    context = {"today": today, "rooms": rooms, "arrivals": arrivals, "departures": departures,
               "total_rooms": len(rooms), "occupied": len(stays), "available": len(free_ids),
               "cleaning_count": sum(room.status == Room.Status.CLEANING for room in rooms),
               "bookings_today": arrivals.count(), "checkins_today": arrivals.filter(status="confirmed").count(),
               "checkouts_today": departures.count(),
               "revenue": Payment.objects.filter(received_at__date=today).aggregate(total=Sum("amount"))["total"] or Decimal("0")}
    return render(request, "core/dashboard.html", context)


def forbidden(request, exception):
    return render(request, "core/error.html", {"code": 403, "title": "Acesso não permitido", "description": "Seu perfil não tem acesso a esta página. Procure o administrador se precisar de ajuda."}, status=403)


def not_found(request, exception):
    return render(request, "core/error.html", {"code": 404, "title": "Página não encontrada", "description": "O endereço pode ter mudado. Volte ao início para continuar."}, status=404)


def server_error(request):
    return render(request, "core/error.html", {"code": 500, "title": "Não foi possível concluir", "description": "Tente novamente. Se o problema continuar, procure o responsável pelo sistema."}, status=500)
