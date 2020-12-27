from django import template
from django.db.models import Count

from website.models import RuneSet

import math

register = template.Library()


@register.filter
def get_sets(runes, bot=False):
    sets = dict()
    broken = False

    for rune in runes:
        if rune is None:
            continue
        if rune.rune_set not in sets.keys():
            sets[rune.rune_set] = {
                'amount': 0,
                'set': rune.rune_set.amount,
            }
        sets[rune.rune_set]['amount'] += 1

    set_names = list()

    total = 0
    for key, val in sets.items():
        equipped_set = math.floor(val['amount'] / val['set'])
        total += equipped_set * val['set']
        for _ in range(equipped_set):
            set_names.append(key)

    if total < 6:
        broken = True

    if bot:
        return set_names, broken
    return set_names
