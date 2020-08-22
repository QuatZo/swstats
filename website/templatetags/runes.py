from django import template
from django.db.models import Count

from website.models import RuneSet

import math

register = template.Library()

@register.filter
def rune_grinded_val(stat, zeros=False):
    if stat == None or stat == '' or not stat:
        if zeros:
            return "0"
        return "-"
    if stat[0] and stat[1]:
        return stat[0] + stat[1]
    elif stat[0] and not stat[1]:
        return stat[0]

@register.filter
def substat_to_number(text):
    try:
        text = float(text.replace('+', '').replace('%', ''))
    except ValueError:
        text = 0
    except AttributeError:
        pass
    return text

@register.filter
def symbol_to_percentage_plus_text(text):
    return text.replace('%', 'percent').replace('+', 'plus')

@register.filter
def percentage_plus_text_to_symbol(text):
    return text.replace('percent', '%').replace('plus', '+')

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
        for _ in range(equipped_set):
            set_names.append(key.name)

    set_names.sort()

    return ' + '.join(set_names)

@register.filter
def get_runes(monsters):
    runes = list()

    for monster in monsters:
        for rune in monster.runes.all():
            runes.append(rune)
    
    return runes

@register.filter
def get_rune_stat_row(primary, value):
    if isinstance(primary, int):
        return ""
        
    value = str(value)
    if '%' in primary:
        value += '%'
    primary = primary.replace('%', '').replace('+', '')

    return primary + ' +' + value

@register.filter
def ancient_to_normal(quality):
    return quality.replace('Ancient ', '')