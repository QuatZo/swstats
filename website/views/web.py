from django.shortcuts import get_object_or_404, render
from django.db.models import F, Q, Avg, Min, Max, Sum, Count
from django.db import connection

from website.models import RuneSet, Rune, Monster, RuneRTA, MonsterBase, MonsterHoh, MonsterFamily, MonsterFusion, Deck, DungeonRun

from datetime import timedelta
import matplotlib.cm as cm
import numpy as np
from operator import itemgetter
import math

# homepage
def get_homepage(request):
    """Return the homepage with carousel messages & introduction."""
    runes = Rune.objects.all()
    monsters = Monster.objects.all()
    rune_best = runes.order_by('-efficiency').first()
    rune_equipped = Rune.objects.filter(equipped=True).count()
    monster_best = monsters.order_by('-avg_eff').first()
    monster_cdmg = monsters.order_by('-crit_dmg').first()
    monster_speed = monsters.order_by('-speed').first()

    MESSAGES = [
        {
            'id': 1,
            'title': 'Highest rune efficiency',
            'text': f'The most efficient rune stored in database has {rune_best.efficiency if rune_best else 0}% efficiency.',
            'type': 'rune',
            'arg': rune_best.id if rune_best else 0,
        },
        {
            'id': 2,
            'title': 'Equipped runes',
            'text': f'From {runes.count()} runes in database, only {rune_equipped} are equipped. it gives us {round(rune_equipped / runes.count() * 100, 2) if runes.count() else 0}% \'useless\' runes.',
        },
        {
            'id': 3,
            'title': 'Highest average efficiency',
            'text': f'{str(monster_best)} has the highest average efficiency, amounting to {monster_best.avg_eff if monster_best else 0}%',
            'type': 'monster',
            'arg': monster_best.id if monster_best else 0,
        },
        {
            'id': 4,
            'title': 'Highest critical damage value',
            'text': f'Highest Critical Damage value has {str(monster_cdmg)} with an amazing {monster_cdmg.crit_dmg if monster_cdmg else 0}%',
            'type': 'monster',
            'arg': monster_cdmg.id if monster_best else 0,
        },
        {
            'id': 5,
            'title': 'Fastest monster',
            'text': f'Can something be faster than Flash? Yes! Such a monster is  {str(monster_speed)} with an amazing {monster_speed.speed if monster_speed else 0} SPD',
            'type': 'monster',
            'arg': monster_speed.id if monster_speed else 0,
        },
    ]

    context = {
        'messages': MESSAGES,
    }

    return render( request, 'website/index.html', context )

# bar chart colors
def create_rgb_colors(length):
    """Return the array of 'length', which contains 'rgba(r, g, b, a)' strings for Chart.js."""
    return [ 'rgba(' + str(int(c[0]*255)) + ', ' + str(int(c[1]*255)) + ', ' + str(int(c[2]*255)) + ', ' + str(.35) + ')' for c in cm.rainbow(np.linspace(0, 1, length))]

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

# monster list w/ filters
def get_monster_list_over_time(monsters):
    """Return amount of monsters acquired over time."""
    temp_monsters = monsters.order_by('created')

    time_values = list()
    time_quantity = list()

    for monster in temp_monsters:
        if (monster.created).strftime("%Y-%m-%d") not in time_values: # only monsters per day
            time_values.append((monster.created).strftime("%Y-%m-%d"))
            time_quantity.append(temp_monsters.filter(created__lte=(monster.created + timedelta(days=1)).strftime("%Y-%m-%d")).count())
    
    return { 'time': time_values, 'quantity': time_quantity }

def get_monster_list_group_by_family(monsters):
    """Return name, amount of families and quantity of monsters for every family in given monsters list."""
    group_by_family = monsters.values('base_monster__family__name').annotate(total=Count('base_monster__family__name')).order_by('-total')

    family_name = list()
    family_count = list()

    for group in group_by_family:
        family_name.append(group['base_monster__family__name'])
        family_count.append(group['total'])

    return { 'name': family_name, 'quantity': family_count, 'length': len(family_name) }

def get_monster_list_best(monsters, x):
    """Return TopX (or all, if there is no X elements in list) efficient monsters."""
    return monsters[:min(x, monsters.count())]

def get_monster_list_fastest(monsters, x):
    """Return TopX (or all, if there is no X elements in list) fastest monsters."""
    fastest_monsters = monsters.order_by(F('speed').desc(nulls_last=True))
    fastest_monsters = fastest_monsters[:min(x, fastest_monsters.count())]

    return fastest_monsters

def get_monster_list_toughest(monsters, x):
    """Return TopX (or all, if there is no X elements in list) toughest (Effective HP) monsters."""
    toughest_monsters = monsters.order_by(F('eff_hp').desc(nulls_last=True))
    toughest_monsters = toughest_monsters[:min(x, toughest_monsters.count())]

    return toughest_monsters

def get_monster_list_toughest_def_break(monsters, x):
    """Return TopX (or all, if there is no X elements in list) toughest (Effective HP while Defense Broken) monsters."""
    toughest_def_break_monsters = monsters.order_by(F('eff_hp_def_break').desc(nulls_last=True))
    toughest_def_break_monsters = toughest_def_break_monsters[:min(x, toughest_def_break_monsters.count())]

    return toughest_def_break_monsters

def get_monster_list_group_by_attribute(monsters):
    """Return names, amount of attributes and quantity of monsters for every attribute in given monsters list."""
    group_by_attribute = monsters.values('base_monster__attribute').annotate(total=Count('base_monster__attribute')).order_by('-total')

    attribute_name = list()
    attribute_count = list()

    for group in group_by_attribute:
        attribute_name.append(MonsterBase(attribute=group['base_monster__attribute']).get_attribute_display())
        attribute_count.append(group['total'])

    return { 'name': attribute_name, 'quantity': attribute_count, 'length': len(attribute_name) }

def get_monster_list_group_by_type(monsters):
    """Return names, amount of types and quantity of monsters for every type in given monsters list."""
    group_by_type = monsters.values('base_monster__archetype').annotate(total=Count('base_monster__archetype')).order_by('-total')

    type_name = list()
    type_count = list()

    for group in group_by_type:
        type_name.append(MonsterBase(archetype=group['base_monster__archetype']).get_archetype_display())
        type_count.append(group['total'])

    return { 'name': type_name, 'quantity': type_count, 'length': len(type_name) }

def get_monster_list_group_by_base_class(monsters):
    """Return number, amount of base class and quantity of monsters for every base class in given monsters list."""
    group_by_base_class = monsters.values('base_monster__base_class').annotate(total=Count('base_monster__base_class')).order_by('base_monster__base_class')

    base_class_number = list()
    base_class_count = list()

    for group in group_by_base_class:
        base_class_number.append(group['base_monster__base_class'])
        base_class_count.append(group['total'])

    return { 'number': base_class_number, 'quantity': base_class_count, 'length': len(base_class_number) }

def get_monster_list_group_by_storage(monsters):
    """Return amount of monsters in/out of storage monsters list."""
    group_by_storage = monsters.values('storage').annotate(total=Count('storage')).order_by('-total')

    storage_value = list()
    storage_count = list()

    for group in group_by_storage:
        storage_value.append(str(group['storage']))
        storage_count.append(group['total'])

    return { 'value': storage_value, 'quantity': storage_count, 'length': len(storage_value) }

def get_monsters_hoh():
    base_monsters_hoh = list()
    for monster_hoh in MonsterHoh.objects.all().only('monster'):
        base_monsters_hoh.append(monster_hoh.monster.id)
        base_monsters_hoh.append(monster_hoh.monster.id + 10) # awakened also

    return base_monsters_hoh

def get_monsters_fusion():
    base_monsters_fusion = list()
    for monster_fusion in MonsterFusion.objects.all().only('monster'):
        base_monsters_fusion.append(monster_fusion.monster.id)
        base_monsters_fusion.append(monster_fusion.monster.id + 10) # awakened also

    return base_monsters_fusion

def get_monster_list_group_by_hoh(monsters):
    """Return amount of monsters which have been & and not in Hall of Heroes."""

    base_monsters_hoh = get_monsters_hoh()
    monsters_hoh = monsters.filter(base_monster__in=base_monsters_hoh)
    monsters_hoh_exclude = monsters.exclude(base_monster__in=base_monsters_hoh)

    hoh_values = list()
    hoh_quantity = list()

    if monsters_hoh.count() > 0:
        hoh_values.append(True)
        hoh_quantity.append(monsters_hoh.count())

    if monsters_hoh_exclude.count() > 0:
        hoh_values.append(False)
        hoh_quantity.append(monsters_hoh_exclude.count())

    return { 'value': hoh_values, 'quantity': hoh_quantity, 'length': len(hoh_values) }

def get_monster_list_group_by_fusion(monsters):
    """Return amount of monsters which have been & and not in Fusion."""

    base_monsters_fusion = get_monsters_fusion()
    monsters_fusion = monsters.filter(base_monster__in=base_monsters_fusion)
    monsters_fusion_exclude = monsters.exclude(base_monster__in=base_monsters_fusion)

    fusion_values = list()
    fusion_quantity = list()

    if monsters_fusion.count() > 0:
        fusion_values.append(True)
        fusion_quantity.append(monsters_fusion.count())

    if monsters_fusion_exclude.count() > 0:
        fusion_values.append(False)
        fusion_quantity.append(monsters_fusion_exclude.count())

    return { 'value': fusion_values, 'quantity': fusion_quantity, 'length': len(fusion_values) }

# specific monster ranking
def get_monster_rank_avg_eff(monsters, monster):
    return monsters.filter(avg_eff__gte=monster.avg_eff).count()

def get_monster_rank_stats(monsters, monster, stat):
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
        return monsters.count()

    rank = 1
    value = stats[stat]

    for temp_monster in monsters.raw(f'SELECT id, {stat} FROM website_monster WHERE {stat} IS NOT NULL'):
        temp_monster = temp_monster.__dict__
        if temp_monster[stat] is not None and temp_monster[stat] > value:
            rank += 1

    return rank

# deck list w/ filters
def get_deck_list_group_by_family(decks):
    """Return name, amount of families and quantity of monsters for every family in given decks list."""
    group_by_family = decks.values('monsters__base_monster__family__name').annotate(total=Count('monsters__base_monster__family__name')).order_by('-total')

    family_name = list()
    family_count = list()

    for group in group_by_family:
        family_name.append(group['monsters__base_monster__family__name'])
        family_count.append(group['total'])

    return { 'name': family_name, 'quantity': family_count, 'length': len(family_name) }

def get_deck_list_group_by_place(decks):
    """Return names, amount of places and quantity of decks for every place in given decks list."""
    group_by_place = decks.values('place').annotate(total=Count('place')).order_by('-total')

    place_name = list()
    place_count = list()

    for group in group_by_place:
        place_name.append(Deck(place=group['place']).get_place_display())
        place_count.append(group['total'])

    return { 'name': place_name, 'quantity': place_count, 'length': len(place_name) }

def get_deck_list_avg_eff(decks):
    """Return the avg efficiency of given deck, incl. decks splitted into two sets (above & equal, below)."""
    if not decks.count():
        return { 'above': [], 'below': [], 'avg': 0 }

    avg_eff = decks.aggregate(Avg('team_runes_eff'))['team_runes_eff__avg']
    avg_eff_above_decks = list()
    avg_eff_below_decks = list()

    for deck in decks:
        if deck.team_runes_eff >= avg_eff:
            avg_eff_above_decks.append({
                'x': deck.id,
                'y': deck.team_runes_eff
            })
        else:
            avg_eff_below_decks.append({
                'x': deck.id,
                'y': deck.team_runes_eff
            })

    return { 'above': avg_eff_above_decks, 'below': avg_eff_below_decks, 'avg': avg_eff }

def get_deck_similar(deck):
    return Deck.objects.filter(place=deck.place, team_runes_eff__range=[deck.team_runes_eff - 10, deck.team_runes_eff + 10]).exclude(id=deck.id)

# dungeons
def get_dungeon_runs_distribution(runs, parts):
    """Return sets of clear times in specific number of parts, to make Distribution chart."""
    if not runs.count():
        return { 'distribution': [], 'scope': [], 'interval': parts }

    fastest = runs.aggregate(Min('clear_time'))['clear_time__min'].total_seconds()
    slowest = runs.aggregate(Max('clear_time'))['clear_time__max'].total_seconds()

    delta = (slowest - fastest) / parts

    points = [(fastest + (delta / 2) + i * delta) for i in range(parts)]
    distribution = [0 for _ in range(parts)]

    for run in runs:
        for i in range(parts):
            left = points[i] - delta / 2
            right = points[i] + delta / 2
            if i == parts - 1:
                if run.clear_time.total_seconds() >= left and run.clear_time.total_seconds() <= right:
                    distribution[i] += 1
                    break
            elif run.clear_time.total_seconds() >= left and run.clear_time.total_seconds() < right:
                    distribution[i] += 1
                    break

    points = [str(timedelta(seconds=round(point))) for point in points]

    return { 'distribution': distribution, 'scope': points, 'interval': parts }

def get_dungeon_runs_by_comp(comps, dungeon_runs, fastest_run, base=False):
    records = list()
    for comp in comps:
        runs = dungeon_runs
        for monster_comp in comp:
            if not base:
                runs = runs.filter(monsters=monster_comp)
            else:
                runs = runs.filter(monsters__base_monster=monster_comp.base_monster)
        
        runs_comp = runs.count()
        wins_comp = runs.filter(win=True).count()

        if not base:
            monsters_in_comp = comp
        else:
            monsters_in_comp = [mon.base_monster for mon in comp]

        record = {
            'comp': monsters_in_comp,
            'average_time': runs.exclude(clear_time__isnull=True).aggregate(avg_time=Avg('clear_time'))['avg_time'],
            'wins': wins_comp,
            'loses': runs_comp - wins_comp,
            'success_rate': round(wins_comp * 100 / runs_comp, 2),
        }

        # sort descending by 'ranking' formula: win_rate / math.exp(average_time.total_seconds / (60 * fastest_run ))
        # 60 - seconds in one minute;
        # visualization for fastest_run = 15: https://www.wolframalpha.com/input/?i=y%2Fexp%28x%2F%2860*15%29%29+for+x%3D15..300%2C+y%3D0..1
        if record['average_time'] is not None:
            record['sorting_val'] = (record['success_rate'] / 100 / math.exp(record['average_time'].total_seconds() / (60 * fastest_run )))
            if not base:
                records.append(record)
            else:
                exists = False
                for temp_record_base in records:
                    if record['comp'] == temp_record_base['comp']:
                        exists = True
                        break
                if not exists:
                    records.append(record)

    return records

def get_dungeon_runs_by_base_class(dungeon_runs):
    base_monsters = dict()
    for record in dungeon_runs.exclude(monsters__isnull=True):
        for monster in record.monsters.all():
            if monster.base_monster.name not in base_monsters.keys():
                base_monsters[monster.base_monster.name] = 0
            base_monsters[monster.base_monster.name] += 1

    base_monsters = {k: base_monsters[k] for k in sorted(base_monsters, key=base_monsters.get, reverse=True)}
    return (list(base_monsters.keys()), list(base_monsters.values()))

# Create your views here.
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

def get_monsters(request):
    monsters = Monster.objects.all().order_by('-avg_eff')   
    is_filter = False 
    filters = list()

    if request.GET:
        is_filter = True

    if request.GET.get('family'):
        family = request.GET.get('family').replace('_', ' ')
        filters.append('Family: ' + family)
        monsters = monsters.filter(base_monster__family__name=family)

    if request.GET.get('attribute'):
        filters.append('Attribute: ' + request.GET.get('attribute'))
        monsters = monsters.filter(base_monster__attribute=MonsterBase().get_attribute_id(request.GET.get('attribute')))

    if request.GET.get('type'):
        filters.append('Type: ' + request.GET.get('type'))
        monsters = monsters.filter(base_monster__archetype=MonsterBase().get_archetype_id(request.GET.get('type')))
    
    if request.GET.get('base-class'):
        filters.append('Base Class: ' + request.GET.get('base-class'))
        monsters = monsters.filter(base_monster__base_class=request.GET.get('base-class'))
    
    if request.GET.get('storage'):
        filters.append('Storage: ' + request.GET.get('storage'))
        monsters = monsters.filter(storage=request.GET.get('storage'))

    if request.GET.get('hoh'):
        filters.append('HoH: ' + request.GET.get('hoh'))
        if request.GET.get('hoh') == "True":
            monsters = monsters.filter(base_monster__in=get_monsters_hoh())
        else:
            monsters = monsters.exclude(base_monster__in=get_monsters_hoh())
    
    if request.GET.get('fusion'):
        filters.append('Fusion: ' + request.GET.get('fusion'))
        if request.GET.get('fusion') == "True":
            monsters = monsters.filter(base_monster__in=get_monsters_fusion())
        else:
            monsters = monsters.exclude(base_monster__in=get_monsters_fusion())

    monsters_over_time = get_monster_list_over_time(monsters)
    monsters_by_family = get_monster_list_group_by_family(monsters)
    monsters_by_attribute = get_monster_list_group_by_attribute(monsters)
    monsters_by_type = get_monster_list_group_by_type(monsters)
    monsters_by_base_class = get_monster_list_group_by_base_class(monsters)
    monsters_by_storage = get_monster_list_group_by_storage(monsters)
    monsters_by_hoh = get_monster_list_group_by_hoh(monsters)
    monsters_by_fusion = get_monster_list_group_by_fusion(monsters)
    best_monsters = get_monster_list_best(monsters, 100)
    fastest_monsters = get_monster_list_fastest(monsters, 100)
    toughest_monsters = get_monster_list_toughest(monsters, 100)
    toughest_def_break_monsters = get_monster_list_toughest_def_break(monsters, 100)

    context = {
        # filters
        'is_filter': is_filter,
        'filters': '[' + ', '.join(filters) + ']',

        # chart monster by acquiration date
        'time_timeline': monsters_over_time['time'],
        'time_count': monsters_over_time['quantity'],

        # chart monster by family
        'family_name': monsters_by_family['name'],
        'family_count': monsters_by_family['quantity'],
        'family_color': create_rgb_colors(monsters_by_family['length']),

        # chart monster by attribute
        'attribute_name': monsters_by_attribute['name'],
        'attribute_count': monsters_by_attribute['quantity'],
        'attribute_color': create_rgb_colors(monsters_by_attribute['length']),

        # chart monster by type (archetype)
        'type_name': monsters_by_type['name'],
        'type_count': monsters_by_type['quantity'],
        'type_color': create_rgb_colors(monsters_by_type['length']),

        # chart monster by base class
        'base_class_number': monsters_by_base_class['number'],
        'base_class_count': monsters_by_base_class['quantity'],
        'base_class_color': create_rgb_colors(monsters_by_base_class['length']),

        # chart monster by storage
        'storage_value': monsters_by_storage['value'],
        'storage_count': monsters_by_storage['quantity'],
        'storage_color': create_rgb_colors(monsters_by_storage['length']),

        # chart monster by hoh
        'hoh_value': monsters_by_hoh['value'],
        'hoh_count': monsters_by_hoh['quantity'],
        'hoh_color': create_rgb_colors(monsters_by_hoh['length']),

        # chart monster by fusion
        'fusion_value': monsters_by_fusion['value'],
        'fusion_count': monsters_by_fusion['quantity'],
        'fusion_color': create_rgb_colors(monsters_by_fusion['length']),

        # table best by efficiency
        'best_monsters': best_monsters,
        'best_amount': len(best_monsters),

        # table best by speed
        'fastest_monsters': fastest_monsters,
        'fastest_amount': len(fastest_monsters),

        # table best by Effective HP
        'toughest_monsters': toughest_monsters,
        'toughest_amount': len(toughest_monsters),

        # table best by Effective HP while Defense Broken
        'toughest_def_break_monsters': toughest_def_break_monsters,
        'toughest_def_break_amount': len(toughest_def_break_monsters),
    }

    return render( request, 'website/monsters/monster_index.html', context)

def get_monster_by_id(request, arg_id):
    monsters = Monster.objects.all().order_by('-avg_eff')
    monster = get_object_or_404(Monster, id=arg_id)
    
    rta_monsters = RuneRTA.objects.filter(monster=arg_id)
    rta_build = list()

    for rta_monster in rta_monsters:
        rta_build.append(rta_monster.rune)
    
    try:
        rta_eff = sum([ rune.efficiency for rune in rta_build ]) / len(rta_build)
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

    ranks = {
        'normal': {
            'avg_eff': get_monster_rank_avg_eff(monsters, monster),
            'hp': get_monster_rank_stats(monsters, monster, 'hp'),
            'attack': get_monster_rank_stats(monsters, monster, 'attack'),
            'defense': get_monster_rank_stats(monsters, monster, 'defense'),
            'speed': get_monster_rank_stats(monsters, monster, 'speed'),
            'res': get_monster_rank_stats(monsters, monster, 'res'),
            'acc': get_monster_rank_stats(monsters, monster, 'acc'),
            'crit_rate': get_monster_rank_stats(monsters, monster, 'crit_rate'),
            'crit_dmg': get_monster_rank_stats(monsters, monster, 'crit_dmg'),
            'eff_hp': get_monster_rank_stats(monsters, monster, 'eff_hp'),
            'eff_hp_def_break': get_monster_rank_stats(monsters, monster, 'eff_hp_def_break'),
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
    }

    context = { 
        'monster': monster, 
        'ranks': ranks,
        'rta': rta,
        'similar': monsters.filter(base_monster__attribute=monster.base_monster.attribute, base_monster__family=monster.base_monster.family, avg_eff__range=[monster.avg_eff - 20, monster.avg_eff + 20]).exclude(id=monster.id),
        'rta_similar': rta_similar_builds,
        'decks': Deck.objects.all().filter(monsters__id=monster.id),
    }

    return render( request, 'website/monsters/monster_by_id.html', context )

def get_decks(request):
    decks = Deck.objects.all().order_by('-team_runes_eff')
    is_filter = False
    filters = list()

    if request.GET:
        is_filter = True

    if request.GET.get('family'):
        family = request.GET.get('family').replace('_', ' ')
        filters.append('Family: ' + family)
        decks = decks.filter(monsters__base_monster__family__name=family)

    if request.GET.get('place'):
        place = request.GET.get('place').replace('_', ' ')
        filters.append('Place: ' + place)
        decks = decks.filter(place=Deck().get_place_id(place))

    decks_by_family = get_deck_list_group_by_family(decks)
    decks_by_place = get_deck_list_group_by_place(decks)
    decks_eff = get_deck_list_avg_eff(decks)

    # needs to be last, because it's for TOP table
    amount = min(100, decks.count())
    decks = decks[:amount]

    context = { 
        # filters
        'is_filter': is_filter,
        'filters': '[' + ', '.join(filters) + ']',
        
        # chart group by family members
        'family_name': decks_by_family['name'],
        'family_count': decks_by_family['quantity'],
        'family_color': create_rgb_colors(decks_by_family['length']),

        # chart group by place
        'place_name': decks_by_place['name'],
        'place_count': decks_by_place['quantity'],
        'place_color': create_rgb_colors(decks_by_place['length']),

        # chart best
        'avg_eff_above_decks': decks_eff['above'],
        'avg_eff_above_quantity': len(decks_eff['above']),
        'avg_eff_below_decks': decks_eff['below'],
        'avg_eff_below_quantity': len(decks_eff['below']),
        'avg_eff': round(decks_eff['avg'], 2),

        # Table TOP decks
        'decks': decks,
        'amount': amount,
    }
    return render( request, 'website/decks/deck_index.html', context)

def get_deck_by_id(request, arg_id):
    deck = get_object_or_404(Deck, id=arg_id)
    decks = Deck.objects.all().order_by('place')

    context = { 
        'deck': deck,
        'similar': get_deck_similar(deck),
    }

    return render( request, 'website/decks/deck_by_id.html', context)

def get_dungeons(request):
    dungeons = DungeonRun.objects.values('dungeon', 'stage', 'win').annotate(avg_time=Avg('clear_time')).annotate(quantity=Count('id')).order_by('dungeon', '-stage', '-win')

    dungeons_base = DungeonRun().get_all_dungeons()

    records = dict()
    for dungeon_base in dungeons_base:
        stages = dict()
        max_stage = 10 if dungeon_base != 'Rift of Worlds' else 5
        for i in range(max_stage, 0, -1):
            stages["B" + str(i)] = {
                'avg_time': None,
                'quantity': None,
                'wins': None,
                'loses': None,
            }
        records[dungeon_base] = stages

    for dungeon in dungeons:
        dungeon_name = DungeonRun().get_dungeon_name(dungeon['dungeon'])
        dungeon_stage = "B" + str(dungeon['stage'])
        dungeon_quantity = dungeon['quantity']

        records[dungeon_name][dungeon_stage] = {
            'avg_time': str(dungeon['avg_time']) if dungeon['avg_time'] else records[dungeon_name][dungeon_stage]['avg_time'],
            'quantity': dungeon_quantity if not records[dungeon_name][dungeon_stage]['quantity'] else records[dungeon_name][dungeon_stage]['quantity'] + dungeon_quantity,
            'wins': dungeon_quantity if dungeon['win'] else records[dungeon_name][dungeon_stage]['wins'],
            'loses': dungeon_quantity if not dungeon['win'] else records[dungeon_name][dungeon_stage]['loses'],
        }

    context = {
        'dungeons': records
    }
    
    return render( request, 'website/dungeons/dungeon_index.html', context)

def get_dungeon_by_stage(request, name, stage):
    is_filter = False
    filters = list()
    names = name.split('-')
    for i in range(len(names)):
        if names[i] != "of":
            names[i] = names[i].capitalize()
    name = ' '.join(names)

    dungeon_runs = DungeonRun.objects.filter(dungeon=DungeonRun().get_dungeon_id(name), stage=stage)

    if request.GET:
        is_filter = True

    if request.GET.get('base'):
        base = request.GET.get('base').replace('_', ' ')
        filters.append('Base Monster: ' + base)
        dungeon_runs = dungeon_runs.filter(monsters__base_monster__name=base)

    runs_distribution = get_dungeon_runs_distribution(dungeon_runs.exclude(clear_time__isnull=True), 20)
    avg_time = dungeon_runs.exclude(clear_time__isnull=True).aggregate(avg_time=Avg('clear_time'))['avg_time']

    comps = list()
    for run in dungeon_runs:
        monsters = list()
        for monster in run.monsters.all():
            monsters.append(monster)
        if monsters not in comps and monsters:
            comps.append(monsters)

    try:
        fastest_run = dungeon_runs.exclude(clear_time__isnull=True).order_by('clear_time').first().clear_time.total_seconds()
    except AttributeError:
        fastest_run = None

    records_personal = sorted(get_dungeon_runs_by_comp(comps, dungeon_runs, fastest_run), key=itemgetter('sorting_val'), reverse = True)
    records_base = sorted(get_dungeon_runs_by_comp(comps, dungeon_runs, fastest_run, True), key=itemgetter('sorting_val'), reverse = True)

    
    base_names, base_quantities = get_dungeon_runs_by_base_class(dungeon_runs)

    context = {
        # filters
        'is_filter': is_filter,
        'filters': '[' + ', '.join(filters) + ']',

        # all
        'name': name,
        'dungeon': dungeon_runs, # all runs for given dungeon
        'stage': stage,
        'avg_time': avg_time,
        
        # chart distribution
        'runs_distribution': runs_distribution['distribution'],
        'runs_means': runs_distribution['scope'],
        'runs_colors': create_rgb_colors(runs_distribution['interval']),

        # chart base
        'base_names': base_names,
        'base_quantity': base_quantities,
        'base_colors': create_rgb_colors(len(base_names)),

        # personal table
        'records_personal': records_personal,
        'records_base': records_base,
    }
    
    return render( request, 'website/dungeons/dungeon_by_stage.html', context)

def get_contribute_info(request):
    return render( request, 'website/contribute.html')

def get_credits(request):
    return render( request, 'website/credits.html')

