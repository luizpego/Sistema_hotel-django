from datetime import timedelta
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, OperationalError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from core.permissions import ADMIN, RECEPTION, roles_required
from .forms import AvailabilityForm, ReservationForm, ReasonForm, DiscountForm
from .models import Reservation
from . import services


@roles_required(ADMIN, RECEPTION)
def reservation_list(request):
    items = Reservation.objects.select_related("guest", "room")
    query, status = request.GET.get("q", "").strip(), request.GET.get("status", "")
    if query:
        items = items.filter(Q(code__icontains=query) | Q(guest__name__icontains=query) | Q(room__number__icontains=query))
    if status:
        items = items.filter(status=status)
    return render(request, "reservas/list.html", {"page_obj": Paginator(items, 25).get_page(request.GET.get("page")),
                  "query": query, "status": status, "statuses": Reservation.Status.choices})


@roles_required(ADMIN, RECEPTION)
def availability(request):
    initial = {"start": timezone.localdate(), "end": timezone.localdate() + timedelta(days=1)}
    form = AvailabilityForm(request.GET or None, initial=initial)
    rooms = None
    if form.is_bound and form.is_valid():
        rooms = list(services.available_rooms(**form.cleaned_data))
        for room in rooms:
            room.estimate = (form.cleaned_data["end"] - form.cleaned_data["start"]).days * room.daily_rate
    return render(request, "reservas/availability.html", {"form": form, "rooms": rooms})


@roles_required(ADMIN, RECEPTION)
def reservation_edit(request, pk=None):
    item = get_object_or_404(Reservation, pk=pk) if pk else None
    initial = {name: request.GET.get(name) for name in ("start", "end", "room", "guest") if request.GET.get(name)}
    form = ReservationForm(request.POST or None, instance=item, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            if item:
                item = services.edit_reservation(pk, actor=request.user, **form.cleaned_data)
            else:
                item = services.create_reservation(actor=request.user, **form.cleaned_data)
            messages.success(request, "Reserva salva. O valor contratado está registrado.")
            return redirect("reservas:detail", pk=item.pk)
        except ValidationError as error:
            form.add_error(None, error.messages)
        except (IntegrityError, OperationalError):
            form.add_error(None, "O quarto foi atualizado por outra operação. Consulte a disponibilidade e tente novamente.")
    return render(request, "reservas/form.html", {"form": form, "reservation": item, "title": "Editar reserva" if pk else "Confirmar nova reserva"})


@roles_required(ADMIN, RECEPTION)
def reservation_detail(request, pk):
    item = get_object_or_404(Reservation.objects.select_related("guest", "room", "created_by", "cancelled_by"), pk=pk)
    return render(request, "reservas/detail.html", {"reservation": item, "payments": item.payments.select_related("received_by")})


@roles_required(ADMIN, RECEPTION)
def action(request, pk, action):
    item = get_object_or_404(Reservation.objects.select_related("guest", "room"), pk=pk)
    labels = {"checkin": "Confirmar entrada", "checkout": "Confirmar saída", "cancel": "Cancelar reserva", "noshow": "Registrar não comparecimento"}
    if action not in labels:
        from django.http import Http404
        raise Http404
    form = ReasonForm(request.POST or None) if action in ("cancel", "noshow") else None
    if request.method == "POST" and (form is None or form.is_valid()):
        try:
            services.transition(pk, actor=request.user, action=action, reason=form.cleaned_data["reason"] if form else "")
            messages.success(request, "Operação concluída e registrada no histórico.")
            return redirect("reservas:detail", pk=pk)
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
        except (IntegrityError, OperationalError):
            messages.error(request, "Outra operação alterou esta hospedagem. Atualize a página e confira a situação.")
    return render(request, "reservas/action.html", {"reservation": item, "title": labels[action], "action": action, "form": form})


@roles_required(ADMIN)
def discount(request, pk):
    item = get_object_or_404(Reservation, pk=pk)
    form = DiscountForm(request.POST or None, initial={"amount": item.discount})
    if request.method == "POST" and form.is_valid():
        try:
            services.apply_discount(pk, actor=request.user, **form.cleaned_data)
            messages.success(request, "Desconto autorizado e registrado.")
            return redirect("reservas:detail", pk=pk)
        except ValidationError as error:
            form.add_error(None, error.messages)
    return render(request, "core/form.html", {"form": form, "title": f"Autorizar desconto · {item.code}", "back_url": "reservas:list"})
