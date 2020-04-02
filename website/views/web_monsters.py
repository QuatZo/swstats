from django.shortcuts import get_object_or_404, render
from django.db.models import F, Q, Avg, Min, Max, Sum, Count

from website.models import *
from .web import create_rgb_colors
from datetime import timedelta

import time
import numpy as np
import pandas as pd

from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.views.decorators.cache import cache_page

CACHE_TTL = getattr(settings, 'CACHE_TTL', DEFAULT_TIMEOUT)

# specific monster ranking
def get_monster_rank_avg_eff(monsters, monster):
    return monsters.filter(avg_eff__gte=monster.avg_eff).count()

def get_monster_rank_stats(monsters, monster, stat, count):
    """Return place of monster based on given stat."""
    stats = {
        'hp': monster.hp,
        'attack': monster.attack,
        'defense': monster.defense,
        'speed': monster.speed,
        'res': monster.res,
        'acc': monster.acc,
        'crit_rate': monster.crit_rate,
        'crit_dmg': monster.crit_dmg,
        'eff_hp': monster.eff_hp,
        'eff_hp_def_break': monster.eff_hp_def_break,
    }

    if stats[stat] is None:
        return count

    rank = 1
    value = stats[stat]

    for temp_monster in monsters.raw(f'SELECT id, {stat} FROM website_monster WHERE {stat} IS NOT NULL'):
        temp_monster = temp_monster.__dict__
        if temp_monster[stat] is not None and temp_monster[stat] > value:
            rank += 1

    return rank

# specific monster records
def get_monster_records(monster):
    siege = monster.siege_defense_monsters.all()
    dungeons = monster.dungeon_monsters.all().distinct('dungeon')
    rifts = monster.rift_dungeon_monsters.all().distinct('dungeon')
    has_records = False
    if siege.exists()  or dungeons.exists() or rifts.exists():
        has_records = True
    return {
        'siege': siege,
        'dungeons': dungeons,
        'rifts': rifts,
        'has': has_records,
    }

# views

# @cache_page(CACHE_TTL) # to check how it works with only Celery, Redis & AJAX without Redis 30min caching
def get_monster_by_id(request, arg_id):
    monsters = Monster.objects.all().order_by('-avg_eff')
    monster = get_object_or_404(Monster.objects.prefetch_related('runes', 'runes__rune_set', 'base_monster', 'runes__equipped_runes', 'runes__equipped_runes__base_monster', 'siege_defense_monsters'), id=arg_id)
    
    rta_monsters = RuneRTA.objects.filter(monster=arg_id).prefetch_related('rune', 'rune__rune_set', 'monster', 'monster__base_monster')
    rta_build = list()

    for rta_monster in rta_monsters:
        rta_build.append(rta_monster.rune)

    try:
        rta_eff = round(sum([ rune.efficiency for rune in rta_build ]) / len(rta_build), 2)
    except ZeroDivisionError:
        rta_eff = None

    monsters_category_base = monsters.filter(base_monster=monster.base_monster)
    monsters_category_family = monsters.filter(base_monster__family=monster.base_monster.family)
    monsters_category_attribute = monsters.filter(base_monster__attribute=monster.base_monster.attribute)
    monsters_category_type = monsters.filter(base_monster__archetype=monster.base_monster.archetype)
    monsters_category_attr_type = monsters.filter(base_monster__attribute=monster.base_monster.attribute, base_monster__archetype=monster.base_monster.archetype)
    monsters_category_base_class = monsters.filter(base_monster__base_class=monster.base_monster.base_class)
    monsters_category_all = monsters_category_attr_type.filter(base_monster__base_class=monster.base_monster.base_class)

    rta_similar_builds = dict()
    for rta_similar in RuneRTA.objects.filter(monster__base_monster__family=monster.base_monster.family, monster__base_monster__attribute=monster.base_monster.attribute).exclude(monster=monster.id):
        if rta_similar.monster not in rta_similar_builds.keys():
            rta_similar_builds[rta_similar.monster] = list()
        rta_similar_builds[rta_similar.monster].append(rta_similar.rune)

    monsters_count = monsters.count()

    ranks = {
        'normal': {
            'avg_eff': get_monster_rank_avg_eff(monsters, monster),
            'hp': get_monster_rank_stats(monsters, monster, 'hp', monsters_count),
            'attack': get_monster_rank_stats(monsters, monster, 'attack', monsters_count),
            'defense': get_monster_rank_stats(monsters, monster, 'defense', monsters_count),
            'speed': get_monster_rank_stats(monsters, monster, 'speed', monsters_count),
            'res': get_monster_rank_stats(monsters, monster, 'res', monsters_count),
            'acc': get_monster_rank_stats(monsters, monster, 'acc', monsters_count),
            'crit_rate': get_monster_rank_stats(monsters, monster, 'crit_rate', monsters_count),
            'crit_dmg': get_monster_rank_stats(monsters, monster, 'crit_dmg', monsters_count),
            'eff_hp': get_monster_rank_stats(monsters, monster, 'eff_hp', monsters_count),
            'eff_hp_def_break': get_monster_rank_stats(monsters, monster, 'eff_hp_def_break', monsters_count),
        },
        'categorized': {
            'avg_eff_base': get_monster_rank_avg_eff(monsters_category_base, monster),
            'avg_eff_family': get_monster_rank_avg_eff(monsters_category_family, monster),
            'avg_eff_attribute': get_monster_rank_avg_eff(monsters_category_attribute, monster),
            'avg_eff_type': get_monster_rank_avg_eff(monsters_category_type, monster),
            'avg_eff_attr_type': get_monster_rank_avg_eff(monsters_category_attr_type, monster),
            'avg_eff_base_class': get_monster_rank_avg_eff(monsters_category_base_class, monster),
            'avg_eff_all': get_monster_rank_avg_eff(monsters_category_all, monster),
        }
    }

    rta = {
        'build': rta_build,
        'eff': rta_eff,
    }

    context = { 
        'monster': monster, 
        'ranks': ranks,
        'rta': rta,
        'similar': monsters.filter(base_monster__attribute=monster.base_monster.attribute, base_monster__family=monster.base_monster.family, avg_eff__range=[monster.avg_eff - 20, monster.avg_eff + 20]).exclude(id=monster.id).prefetch_related('runes', 'runes__rune_set', 'base_monster', 'base_monster__family'),
        'rta_similar': rta_similar_builds,
        'decks': Deck.objects.all().filter(monsters__id=monster.id).prefetch_related('monsters', 'monsters__base_monster', 'leader', 'leader__base_monster'),
        'records': get_monster_records(monster),
    }

    return render( request, 'website/monsters/monster_by_id.html', context )
