from decimal import Decimal
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, OperationalError
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from core.forms import PeriodForm
from core.permissions import ADMIN, RECEPTION, roles_required
from reservas.models import Reservation
from .forms import PaymentForm
from .models import Payment
from .services import record_payment


@roles_required(ADMIN, RECEPTION)
def payment_create(request, pk):
    item = get_object_or_404(Reservation.objects.select_related("guest", "room"), pk=pk)
    form = PaymentForm(request.POST or None, initial={"amount": item.balance})
    if request.method == "POST" and form.is_valid():
        try:
            record_payment(pk, actor=request.user, **form.cleaned_data)
            messages.success(request, "Pagamento registrado. O saldo foi atualizado.")
            return redirect("reservas:detail", pk=pk)
        except ValidationError as error:
            form.add_error(None, error.messages)
        except (IntegrityError, OperationalError):
            form.add_error(None, "O registro foi alterado por outra operação. Confira os pagamentos antes de tentar novamente.")
    return render(request, "financeiro/payment.html", {"form": form, "reservation": item})


@roles_required(ADMIN)
def summary(request):
    today = timezone.localdate()
    form = PeriodForm(request.GET or None, initial={"start": today.replace(day=1), "end": today})
    start, end = today.replace(day=1), today
    valid = not form.is_bound or form.is_valid()
    if form.is_bound and valid:
        start, end = form.cleaned_data.get("start") or start, form.cleaned_data.get("end") or end
        if end < start:
            form.add_error(None, "A data final precisa ser posterior à inicial.")
            valid = False
    payments = Payment.objects.select_related("reservation__guest", "reservation__room", "received_by")
    payments = payments.filter(received_at__date__gte=start, received_at__date__lte=end) if valid else payments.none()
    pending = Reservation.objects.filter(status__in=["pending", "confirmed", "in_house"]).select_related("guest", "room").annotate(received=Sum("payments__amount"))
    pending = [item for item in pending if item.total - (item.received or 0) > 0]
    return render(request, "financeiro/summary.html", {
        "form": form, "start": start, "end": end, "total": payments.aggregate(value=Sum("amount"))["value"] or Decimal("0"),
        "daily": Payment.objects.filter(received_at__date=today).aggregate(v=Sum("amount"))["v"] or 0,
        "monthly": Payment.objects.filter(received_at__date__gte=today.replace(day=1), received_at__date__lte=today).aggregate(v=Sum("amount"))["v"] or 0,
        "pending": pending, "pending_total": sum((r.total - (r.received or 0) for r in pending), Decimal("0")),
        "by_method": [{"label": label, "total": payments.filter(method=key).aggregate(v=Sum("amount"))["v"] or 0} for key, label in Payment.Method.choices],
        "page_obj": Paginator(payments, 30).get_page(request.GET.get("page")),
    })
