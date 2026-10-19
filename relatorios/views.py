import time
import uuid
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from core.forms import PeriodForm
from core.permissions import ADMIN, RECEPTION, allowed, roles_required
from .excel import HEADERS, LABELS, commit_import, export_data, import_template, preview_import
from .forms import ImportForm


@roles_required(ADMIN, RECEPTION)
def index(request):
    today = timezone.localdate()
    form = PeriodForm(request.GET or None, initial={"start": today.replace(day=1), "end": today})
    kinds = [(key, value) for key, value in LABELS.items() if allowed(request.user, ADMIN) or key not in ("payments", "financial")]
    return render(request, "relatorios/index.html", {"form": form, "kinds": kinds})


@roles_required(ADMIN, RECEPTION)
def export(request, kind):
    form = PeriodForm(request.GET)
    if form.is_valid():
        today = timezone.localdate()
        start = form.cleaned_data.get("start") or today.replace(day=1)
        end = form.cleaned_data.get("end") or today
        try:
            return export_data(kind, start, end, request.user)
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
    else:
        messages.error(request, "Confira as datas do relatório.")
    return redirect("relatorios:index")


@roles_required(ADMIN, RECEPTION)
def template(request, kind):
    if kind == "rooms" and not allowed(request.user, ADMIN):
        raise PermissionDenied
    if kind not in HEADERS:
        from django.http import Http404
        raise Http404
    return import_template(kind)


@roles_required(ADMIN, RECEPTION)
def import_file(request):
    form = ImportForm(request.POST or None, request.FILES or None)
    if not allowed(request.user, ADMIN):
        form.fields["kind"].choices = [("guests", "Hóspedes")]
    if request.method == "POST" and form.is_valid():
        kind = form.cleaned_data["kind"]
        try:
            rows, errors = preview_import(form.cleaned_data["file"], kind)
            token = uuid.uuid4().hex
            request.session["excel_preview"] = {"kind": kind, "rows": rows, "token": token,
                                                "at": time.time(), "user": request.user.pk}
            return render(request, "relatorios/preview.html", {"rows": rows[:50], "count": len(rows), "errors": errors,
                          "headers": HEADERS[kind], "token": token, "kind_label": LABELS[kind]})
        except ValidationError as error:
            form.add_error(None, error.messages)
    return render(request, "relatorios/import.html", {"form": form})


@roles_required(ADMIN, RECEPTION)
def confirm_import(request):
    from django.views.decorators.http import require_POST
    if request.method != "POST":
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(["POST"])
    preview = request.session.get("excel_preview", {})
    if (not preview or preview.get("user") != request.user.pk or time.time() - preview.get("at", 0) > 900 or
            not constant_time_compare(request.POST.get("token", ""), preview.get("token", ""))):
        messages.error(request, "A prévia expirou. Envie a planilha novamente para conferir os dados.")
        return redirect("relatorios:import")
    try:
        count = commit_import(preview["kind"], preview["rows"], request.user)
        request.session.pop("excel_preview", None)
        messages.success(request, f"{count} cadastros importados com sucesso.")
    except ValidationError as error:
        request.session.pop("excel_preview", None)
        messages.error(request, "A importação foi cancelada. " + " ".join(error.messages[:5]))
    except IntegrityError:
        request.session.pop("excel_preview", None)
        messages.error(request, "Outro cadastro foi criado durante a conferência. Nada foi importado; envie a planilha novamente.")
    return redirect("relatorios:import")
