from django import template
from django.db.models import Count

from website.models import RuneSet
register = template.Library()

import math

@register.filter
def get_set_names(runes):
    sets = dict()
    for rune in runes:
        if rune.rune_set not in sets.keys():
            sets[rune.rune_set] = {
                'amount': 0,
                'set': rune.rune_set.amount,
            }
        sets[rune.rune_set]['amount'] += 1

    set_names = list()

    for key, val in sets.items():
        equipped_set = math.floor(val['amount'] / val['set'])
        for i in range(equipped_set):
            set_names.append(key.name)

    set_names.sort()

    return ' + '.join(set_names)