from decimal import Decimal
from django import template
from django.utils.formats import number_format

register = template.Library()


@register.filter
def brl(value):
    return "R$ " + number_format(Decimal(value or 0), decimal_pos=2, use_l10n=True, force_grouping=True)
