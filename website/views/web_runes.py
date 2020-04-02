from django.shortcuts import get_object_or_404, render
from django.db.models import F, Q, Avg, Min, Max, Sum, Count
from website.models import *

from .web import create_rgb_colors

from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.views.decorators.cache import cache_page

CACHE_TTL = getattr(settings, 'CACHE_TTL', DEFAULT_TIMEOUT)

# specific rune
def get_rune_rank_eff(runes, rune):
    """Return place of rune based on efficiency."""
    return runes.filter(efficiency__gte=rune.efficiency).count()

def get_rune_rank_substat(runes, rune, substat, filters=None):
    """Return place of rune based on given substat."""
    substats = {
        'sub_hp_flat': rune.sub_hp_flat,
        'sub_hp': rune.sub_hp,
        'sub_atk_flat': rune.sub_atk_flat,
        'sub_atk': rune.sub_atk,
        'sub_def_flat': rune.sub_def_flat,
        'sub_def': rune.sub_def,
        'sub_speed': rune.sub_speed,
        'sub_crit_rate': rune.sub_crit_rate,
        'sub_crit_dmg': rune.sub_crit_dmg,
        'sub_res': rune.sub_res,
        'sub_acc': rune.sub_acc,
    }

    if substats[substat] is None:
        return None

    remaining_filters = ""
    if filters:
        if 'slot' in filters:
            remaining_filters += "AND slot=" + str(rune.slot)
        if 'set' in filters:
            remaining_filters += "AND rune_set_id=" + str(rune.rune_set.id)

    rank = 1
    value = sum(substats[substat])

    for temp_rune in runes.raw(f'SELECT id, {substat} FROM website_rune WHERE {substat} IS NOT NULL {remaining_filters}'):
        temp_rune = temp_rune.__dict__
        if temp_rune[substat] is not None and sum(temp_rune[substat]) > value:
            rank += 1

    return rank

def get_rune_similar(runes, rune):
    """Return runes similar to the given one."""
    return runes.filter(slot=rune.slot, rune_set=rune.rune_set, primary=rune.primary, efficiency__range=[rune.efficiency - 15, rune.efficiency + 15]).exclude(id=rune.id).order_by('-efficiency').prefetch_related('equipped_runes', 'equipped_runes__base_monster', 'rune_set')

# views
# @cache_page(CACHE_TTL) # to check how it works with only Celery, Redis & AJAX without Redis 30min caching
def get_rune_by_id(request, arg_id):
    rune = get_object_or_404(Rune.objects.prefetch_related('rune_set', 'equipped_runes', 'equipped_runes__base_monster', 'equipped_runes__runes', 'equipped_runes__runes__rune_set' ), id=arg_id)
    runes = Rune.objects.all()

    try:
        rta_monster = RuneRTA.objects.filter(rune=rune.id).prefetch_related('monster', 'monster__base_monster', 'rune', 'rune__rune_set').first().monster
    except AttributeError:
        rta_monster = None

    runes_category_slot = runes.filter(slot=rune.slot)
    runes_category_set = runes.filter(rune_set=rune.rune_set)
    runes_category_both = runes.filter(slot=rune.slot, rune_set=rune.rune_set)

    runes_count = runes.count()

    ranks = {
        'normal': {
            'efficiency': get_rune_rank_eff(runes, rune),
            'hp_flat': get_rune_rank_substat(runes, rune, 'sub_hp_flat'),
            'hp': get_rune_rank_substat(runes, rune, 'sub_hp'),
            'atk_flat': get_rune_rank_substat(runes, rune, 'sub_atk_flat'),
            'atk': get_rune_rank_substat(runes, rune, 'sub_atk'),
            'def_flat': get_rune_rank_substat(runes, rune, 'sub_def_flat'),
            'def': get_rune_rank_substat(runes, rune, 'sub_def'),
            'speed': get_rune_rank_substat(runes, rune, 'sub_speed'),
            'crit_rate': get_rune_rank_substat(runes, rune, 'sub_crit_rate'),
            'crit_dmg': get_rune_rank_substat(runes, rune, 'sub_crit_dmg'),
            'res': get_rune_rank_substat(runes, rune, 'sub_res'),
            'acc': get_rune_rank_substat(runes, rune, 'sub_acc'),
        },
        'categorized': {
            'efficiency_slot': get_rune_rank_eff(runes_category_slot, rune),
            'efficiency_set': get_rune_rank_eff(runes_category_set, rune),
            'efficiency_both': get_rune_rank_eff(runes_category_both, rune),
            'speed_slot': get_rune_rank_substat(runes_category_slot, rune, 'sub_speed', ['slot']),
            'speed_set': get_rune_rank_substat(runes_category_set, rune, 'sub_speed', ['set']),
            'speed_both': get_rune_rank_substat(runes_category_both, rune, 'sub_speed', ['slot', 'set']),
        }
    }

    context = { 
        'rune': rune, 
        'rta_monster': rta_monster,
        'ranks': ranks,
        'similar_runes': get_rune_similar(runes, rune),
    }

    return render( request, 'website/runes/rune_by_id.html', context )
