from django.contrib import messages
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from core.models import audit
from core.permissions import ADMIN, RECEPTION, roles_required
from .forms import GuestForm
from .models import Guest


@roles_required(ADMIN, RECEPTION)
def guest_list(request):
    query = request.GET.get("q", "").strip()
    items = Guest.objects.all()
    if query:
        items = items.filter(Q(name__icontains=query) | Q(cpf__icontains=query.replace(".", "").replace("-", "")) | Q(phone__icontains=query))
    return render(request, "hospedes/list.html", {"page_obj": Paginator(items, 25).get_page(request.GET.get("page")), "query": query})


@roles_required(ADMIN, RECEPTION)
def guest_edit(request, pk=None):
    item = get_object_or_404(Guest, pk=pk) if pk else None
    form = GuestForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                item = form.save()
                audit(request.user, "hospede.salvo", item)
            messages.success(request, "Cadastro do hóspede salvo.")
            return redirect("hospedes:detail", pk=item.pk)
        except (IntegrityError, ValidationError):
            form.add_error(None, "Já existe um cadastro com estes dados. Confira o CPF, o nome e o telefone.")
    return render(request, "core/form.html", {"form": form, "title": "Editar hóspede" if pk else "Novo hóspede", "back_url": "hospedes:list"})


@roles_required(ADMIN, RECEPTION)
def guest_detail(request, pk):
    item = get_object_or_404(Guest, pk=pk)
    return render(request, "hospedes/detail.html", {"guest": item, "reservations": item.reservations.select_related("room")})
