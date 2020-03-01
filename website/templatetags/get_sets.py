from django import template
from django.db.models import Count

from website.models import RuneSet
register = template.Library()

import math

@register.filter
def get_sets(runes):
    sets = runes.values('rune_set__name', 'rune_set__amount').annotate(total=Count('rune_set')).order_by()

    set_names = list()

    for _set in sets:
        equipped_set = math.floor(_set['total'] / _set['rune_set__amount'])
        for i in range(equipped_set):
            set_names.append(_set['rune_set__name'])

    return set_names