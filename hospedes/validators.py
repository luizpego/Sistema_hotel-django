import re
from django.core.exceptions import ValidationError


def normalize_cpf(value):
    value = (value or "").strip()
    if value and re.search(r"[^0-9.\-\s]", value):
        raise ValidationError("O CPF deve conter apenas números, pontos e traço.")
    return re.sub(r"\D", "", value)


def validate_cpf(value):
    value = normalize_cpf(value)
    if not value:
        return
    if len(value) != 11 or len(set(value)) == 1:
        raise ValidationError("Informe um CPF válido com 11 dígitos.")
    for size in (9, 10):
        digit = (sum(int(value[i]) * (size + 1 - i) for i in range(size)) * 10) % 11
        if int(value[size]) != (digit if digit < 10 else 0):
            raise ValidationError("O CPF informado não é válido. Confira os dígitos.")
