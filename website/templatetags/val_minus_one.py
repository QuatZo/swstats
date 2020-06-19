from django import template
from website.models import MonsterBase


register = template.Library()

@register.filter
def val_minus_one(val):
    return val - 1