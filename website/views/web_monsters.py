from django.shortcuts import get_object_or_404, render
from django.db.models import F, Q, Avg, Min, Max, Sum, Count

from website.models import *
from .web import create_rgb_colors
from datetime import timedelta

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
    to_exclude = [ 142, 143, 182, 151 ] # Angelmon, Rainbowmon, King Angelmon, Devilmon
    group_by_family = monsters.exclude(base_monster__family__in=to_exclude).values('base_monster__family__name').annotate(total=Count('base_monster__family__name')).order_by('-total')

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

# views
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
