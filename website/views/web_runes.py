from django.shortcuts import get_object_or_404, render
from django.db.models import F, Avg, Min, Max, Sum, Count
from website.models import *

from .web import create_rgb_colors

# rune list w/ filters
def get_rune_list_avg_eff(runes):
    """Return the avg efficiency of given runes, incl. these runes splitted into two sets (above & equal, below)."""
    if not runes.count():
        return { 'above': [], 'below': [], 'avg': 0 }

    avg_eff = runes.aggregate(Avg('efficiency'))['efficiency__avg']
    avg_eff_above_runes = list()
    avg_eff_below_runes = list()

    for rune in runes:
        if rune.efficiency >= avg_eff:
            avg_eff_above_runes.append({
                'x': rune.id,
                'y': rune.efficiency
            })
        else:
            avg_eff_below_runes.append({
                'x': rune.id,
                'y': rune.efficiency
            })

    return { 'above': avg_eff_above_runes, 'below': avg_eff_below_runes, 'avg': avg_eff }

def get_rune_list_normal_distribution(runes, parts):
    """Return sets of runes in specific number of parts, to make Normal Distribution chart."""
    if not runes.count():
        return { 'distribution': [], 'scope': [], 'interval': parts }

    min_eff = runes.aggregate(Min('efficiency'))['efficiency__min']
    max_eff = runes.aggregate(Max('efficiency'))['efficiency__max']
    delta = (max_eff - min_eff) / parts

    points = [round(min_eff + (delta / 2) + i * delta, 2) for i in range(parts)]
    distribution = [0 for _ in range(parts)]

    for rune in runes:
        for i in range(parts):
            left = round(points[i] - delta / 2, 2)
            right = round(points[i] + delta / 2, 2)
            if i == parts - 1:
                if rune.efficiency >= left and rune.efficiency <= right:
                    distribution[i] += 1
                    break
            elif rune.efficiency >= left and rune.efficiency < right:
                    distribution[i] += 1
                    break

    return { 'distribution': distribution, 'scope': points, 'interval': parts }

def get_rune_list_best(runes, x):
    """Return TopX (or all, if there is no X elements in list) efficient runes."""
    return runes[:min(x, runes.count())]

def get_rune_list_fastest(runes, x):
    """Return TopX (or all, if there is no X elements in list) fastest runes."""
    fastest_runes = runes.order_by(F('sub_speed').desc(nulls_last=True))
    fastest_runes = fastest_runes[:min(x, fastest_runes.count())]

    return fastest_runes

def get_rune_list_grouped_by_set(runes):
    """Return names, amount of sets and quantity of runes in every set in given runes list."""
    group_by_set = runes.values('rune_set__name').annotate(total=Count('rune_set')).order_by('-total')
    set_name = list()
    set_count = list()

    for group in group_by_set:
        set_name.append(group['rune_set__name'])
        set_count.append(group['total'])

    return { 'name': set_name, 'quantity': set_count, 'length': len(set_name) }

def get_rune_list_grouped_by_slot(runes):
    """Return numbers, amount of slots and quantity of runes for every slot in given runes list."""
    group_by_slot = runes.values('slot').annotate(total=Count('slot')).order_by('slot')
    slot_number = list()
    slot_count = list()

    for group in group_by_slot:
        slot_number.append(group['slot'])
        slot_count.append(group['total'])

    return { 'number': slot_number, 'quantity': slot_count, 'length': len(slot_number) }

def get_rune_list_grouped_by_quality(runes):
    """Return names, amount of qualities and quantity of runes for every quality in given runes list."""
    group_by_quality = runes.values('quality').annotate(total=Count('quality')).order_by('-total')
    quality_name = list()
    quality_count = list()

    for group in group_by_quality:
        quality_name.append(Rune().get_rune_quality(group['quality']))
        quality_count.append(group['total'])

    return { 'name': quality_name, 'quantity': quality_count, 'length': len(quality_name) }

def get_rune_list_grouped_by_quality_original(runes):
    """Return names, amount of qualities and quantity of runes for every original quality in given runes list."""
    group_by_quality_original = runes.values('quality_original').annotate(total=Count('quality_original')).order_by('-total')
    quality_original_name = list()
    quality_original_count = list()

    for group in group_by_quality_original:
        quality_original_name.append(Rune().get_rune_quality(group['quality_original']))
        quality_original_count.append(group['total'])

    return { 'name': quality_original_name, 'quantity': quality_original_count, 'length': len(quality_original_name) }

def get_rune_list_grouped_by_main_stat(runes):
    """Return names, amount of qualities and quantity of runes for every main stat type in given runes list."""
    group_by_main_stat = runes.values('primary').annotate(total=Count('primary')).order_by('-total')
    main_stat_name = list()
    main_stat_count = list()

    for group in group_by_main_stat:
        main_stat_name.append(Rune().get_rune_primary(group['primary']))
        main_stat_count.append(group['total'])

    return { 'name': main_stat_name, 'quantity': main_stat_count, 'length': len(main_stat_name) }

def get_rune_list_grouped_by_stars(runes):
    """Return numbers, amount of stars and quantity of runes for every star in given runes list."""
    group_by_stars = runes.values('stars').annotate(total=Count('stars')).order_by('stars')
    stars = dict()
    stars_number = list()
    stars_count = list()

    for group in group_by_stars:
        temp_stars = group['stars'] % 10 # ancient runes have 11-16 stars, instead of 1-6
        if temp_stars not in stars.keys():
            stars[temp_stars] = 0
        stars[temp_stars] += group['total']

    for key, val in stars.items():
        stars_number.append(key)
        stars_count.append(val)

    return { 'number': stars_number, 'quantity': stars_count, 'length': len(stars_number) }

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
        return runes.count()

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
    return runes.filter(slot=rune.slot, rune_set=rune.rune_set, primary=rune.primary, efficiency__range=[rune.efficiency - 15, rune.efficiency + 15]).exclude(id=rune.id).order_by('-efficiency')

# views
def get_runes(request):
    runes = Rune.objects.all().order_by('-efficiency')   
    is_filter = False 
    filters = list()

    if request.GET:
        is_filter = True

    if request.GET.get('set'):
        filters.append('Set: ' + request.GET.get('set'))
        runes = runes.filter(rune_set__name=request.GET.get('set'))

    if request.GET.get('slot'):
        try:
            slot = int(request.GET.get('slot'))
        except ValueError:
            slot = 0
        filters.append('Slot: ' + str(slot))
        runes = runes.filter(slot=slot)
    
    if request.GET.get('quality'):
        filters.append('Quality: ' + request.GET.get('quality'))
        quality_id = Rune().get_rune_quality_id(request.GET.get('quality'))
        runes = runes.filter(quality=quality_id)
    
    if request.GET.get('quality-original'):
        filters.append('Original Quality: ' + request.GET.get('quality-original'))
        quality_original_id = Rune().get_rune_quality_id(request.GET.get('quality-original'))
        runes = runes.filter(quality_original=quality_original_id)

    if request.GET.get('main-stat'):
        main_stat = request.GET.get('main-stat').replace('plus', '+').replace('percent', '%')
        filters.append('Main Stat: ' + main_stat)
        main_stat_id = Rune().get_rune_primary_id(main_stat)
        runes = runes.filter(primary=main_stat_id)
    
    if request.GET.get('stars'):
        try:
            stars = int(request.GET.get('stars')) % 10
        except ValueError:
            stars = 0
        filters.append('Stars: ' + str(stars))
        runes = runes.filter(Q(stars=stars) | Q(stars=stars + 10)) # since ancient runes have 11-16

    avg_eff_runes = get_rune_list_avg_eff(runes)
    normal_distribution_runes = get_rune_list_normal_distribution(runes, 40)
    runes_by_set = get_rune_list_grouped_by_set(runes)
    runes_by_slot = get_rune_list_grouped_by_slot(runes)
    runes_by_quality = get_rune_list_grouped_by_quality(runes)
    runes_by_quality_original = get_rune_list_grouped_by_quality_original(runes)
    runes_by_main_stat = get_rune_list_grouped_by_main_stat(runes)
    runes_by_stars = get_rune_list_grouped_by_stars(runes)
    best_runes = get_rune_list_best(runes, 100)
    fastest_runes = get_rune_list_fastest(runes, 100)

    context = {
        # filters
        'is_filter': is_filter,
        'filters': '[' + ', '.join(filters) + ']',

        # chart best
        'avg_eff_above_runes': avg_eff_runes['above'],
        'avg_eff_above_quantity': len(avg_eff_runes['above']),
        'avg_eff_below_runes': avg_eff_runes['below'],
        'avg_eff_below_quantity': len(avg_eff_runes['below']),
        'avg_eff': round(avg_eff_runes['avg'], 2),

        # chart distribution
        'all_distribution': normal_distribution_runes['distribution'],
        'all_means': normal_distribution_runes['scope'],
        'all_color': create_rgb_colors(normal_distribution_runes['interval']),

        # chart group by set
        'set_name': runes_by_set['name'],
        'set_count': runes_by_set['quantity'],
        'set_color': create_rgb_colors(runes_by_set['length']),

        # chart group by slot
        'slot_number': runes_by_slot['number'],
        'slot_count': runes_by_slot['quantity'],
        'slot_color': create_rgb_colors(runes_by_slot['length']),

        # chart group by quality
        'quality_name': runes_by_quality['name'],
        'quality_count': runes_by_quality['quantity'],
        'quality_color': create_rgb_colors(runes_by_quality['length']),

        # chart group by original quality
        'quality_original_name': runes_by_quality_original['name'],
        'quality_original_count': runes_by_quality_original['quantity'],
        'quality_original_color': create_rgb_colors(runes_by_quality_original['length']),

        # chart group by main stat
        'main_stat_name': runes_by_main_stat['name'],
        'main_stat_count': runes_by_main_stat['quantity'],
        'main_stat_color': create_rgb_colors(runes_by_main_stat['length']),

        # chart group by stars
        'stars_number': runes_by_stars['number'],
        'stars_count': runes_by_stars['quantity'],
        'stars_color': create_rgb_colors(runes_by_stars['length']),

        # table best by efficiency
        'best_runes': best_runes,
        'best_amount': len(best_runes),

        # table best by speed
        'fastest_runes': fastest_runes,
        'fastest_amount': len(fastest_runes),
    }

    return render( request, 'website/runes/rune_index.html', context)

def get_rune_by_id(request, arg_id):
    rune = get_object_or_404(Rune, id=arg_id)
    runes = Rune.objects.all()
    monster = Monster.objects.filter(runes__id=rune.id).first()
    try:
        rta_monster = RuneRTA.objects.filter(rune=rune.id).first().monster
    except AttributeError:
        rta_monster = None

    runes_category_slot = runes.filter(slot=rune.slot)
    runes_category_set = runes.filter(rune_set=rune.rune_set)
    runes_category_both = runes.filter(slot=rune.slot, rune_set=rune.rune_set)

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
        'monster': monster, 
        'rta_monster': rta_monster,
        'ranks': ranks,
        'similar_runes': get_rune_similar(runes, rune),
    }

    return render( request, 'website/runes/rune_by_id.html', context )
