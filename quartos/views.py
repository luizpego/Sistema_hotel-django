from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from core.permissions import ADMIN, RECEPTION, CLEANING, roles_required
from .forms import RoomForm, BlockForm
from .models import Room
from . import services


@roles_required(ADMIN, RECEPTION)
def room_list(request):
    rooms = Room.objects.all()
    category, status = request.GET.get("category", ""), request.GET.get("status", "")
    if category:
        rooms = rooms.filter(category=category)
    if status:
        rooms = rooms.filter(status=status)
    occupied = set(Room.objects.filter(reservations__status="in_house").values_list("pk", flat=True))
    rooms = list(rooms)
    for room in rooms:
        room.occupied = room.pk in occupied
    return render(request, "quartos/list.html", {"rooms": rooms, "categories": Room.Category.choices,
                  "statuses": Room.Status.choices, "category": category, "status": status})


@roles_required(ADMIN)
def room_edit(request, pk=None):
    item = get_object_or_404(Room, pk=pk) if pk else None
    form = RoomForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        try:
            item = services.save_room(actor=request.user, data=form.cleaned_data, pk=pk)
            messages.success(request, "Quarto salvo com sucesso.")
            return redirect("quartos:detail", pk=item.pk)
        except ValidationError as error:
            form.add_error(None, error.messages)
        except IntegrityError:
            form.add_error(None, "Já existe um quarto com esse número.")
    return render(request, "core/form.html", {"form": form, "title": "Editar quarto" if pk else "Novo quarto", "back_url": "quartos:list"})


@roles_required(ADMIN, RECEPTION)
def room_detail(request, pk):
    room = get_object_or_404(Room, pk=pk)
    return render(request, "quartos/detail.html", {"room": room, "blocks": room.blocks.filter(active=True),
                  "reservations": room.reservations.filter(status__in=["pending", "confirmed", "in_house"]).select_related("guest")})


@roles_required(ADMIN, CLEANING)
def cleaning(request):
    return render(request, "quartos/cleaning.html", {"rooms": Room.objects.filter(active=True, status=Room.Status.CLEANING)})


@roles_required(ADMIN, CLEANING)
@require_POST
def release(request, pk):
    get_object_or_404(Room, pk=pk)
    try:
        services.release_cleaning(pk, actor=request.user)
        messages.success(request, "Limpeza concluída. Quarto liberado para uso.")
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
    return redirect("quartos:cleaning")


@roles_required(ADMIN)
def block(request, pk):
    room = get_object_or_404(Room, pk=pk)
    form = BlockForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            services.block_room(pk, actor=request.user, **form.cleaned_data)
            messages.success(request, "Bloqueio do período registrado.")
            return redirect("quartos:detail", pk=pk)
        except ValidationError as error:
            form.add_error(None, error.messages)
    return render(request, "core/form.html", {"form": form, "title": f"Bloquear quarto {room.number}", "back_url": "quartos:list"})


@roles_required(ADMIN)
@require_POST
def unblock(request, pk):
    from .models import RoomBlock
    item = get_object_or_404(RoomBlock, pk=pk)
    services.unblock(pk, actor=request.user)
    messages.success(request, "Bloqueio removido.")
    return redirect("quartos:detail", pk=item.room_id)
