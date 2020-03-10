from django.shortcuts import get_object_or_404, render
from django.db.models import F, Q, Avg, Min, Max, Sum, Count

from website.models import *
from .web import create_rgb_colors

from datetime import timedelta
from operator import itemgetter
import math

from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.views.decorators.cache import cache_page

CACHE_TTL = getattr(settings, 'CACHE_TTL', DEFAULT_TIMEOUT)

# dungeons
def get_dungeon_runs_distribution(runs, parts):
    """Return sets of clear times in specific number of parts, to make Distribution chart."""
    if not runs.exists():
        return { 'distribution': [], 'scope': [], 'interval': parts }

    min_max = runs.aggregate(fastest=Min('clear_time'), slowest=Max('clear_time'))
    fastest = min_max['fastest'].total_seconds()
    slowest = min_max['slowest'].total_seconds()

    delta = (slowest - fastest) / parts
    points = [(fastest + (delta / 2) + i * delta) for i in range(parts)]
    distribution = [0 for _ in range(parts)]

    i = 0
    right = points[i] + delta / 2
    for run in runs:
        clear_time = run.clear_time.total_seconds()
        while clear_time > right and i < parts - 1:
            i += 1
            right += delta
        distribution[i] += 1

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
    for record in dungeon_runs:
        for monster in record.monsters.all():
            if monster.base_monster.name not in base_monsters.keys():
                base_monsters[monster.base_monster.name] = 0
            base_monsters[monster.base_monster.name] += 1

    base_monsters = {k: base_monsters[k] for k in sorted(base_monsters, key=base_monsters.get, reverse=True)}
    return (list(base_monsters.keys()), list(base_monsters.values()))

# rift dungeons
def get_rift_dungeon_damage_distribution(runs, parts):
    """Return sets of damages in specific number of parts, to make Distribution chart."""
    if not runs.exists():
        return { 'distribution': [], 'scope': [], 'interval': parts }

    min_max = runs.aggregate(lowest=Min('dmg_total'), highest=Max('dmg_total'))
    lowest = min_max['lowest']
    highest = min_max['highest']

    delta = (highest - lowest) / parts
    points = [(lowest + (delta / 2) + i * delta) for i in range(parts)]
    distribution = [0 for _ in range(parts)]

    i = 0
    right = points[i] + delta / 2
    for run in runs:
        dmg_total = run.dmg_total
        while dmg_total > right and i < parts - 1:
            i += 1
            right += delta
        distribution[i] += 1

    points = [str(round(point)) for point in points]

    return { 'distribution': distribution, 'scope': points, 'interval': parts }

def get_rift_dungeon_runs_by_comp(comps, dungeon_runs, highest_damage, base=False):
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

        most_freq_rating = runs.values('win', 'clear_rating').annotate(rank=Count('clear_rating')).order_by('-win').first()['clear_rating']

        record = {
            'comp': monsters_in_comp,
            'average_time': runs.exclude(clear_time__isnull=True).aggregate(avg_time=Avg('clear_time'))['avg_time'],
            'most_freq_rating': RiftDungeonRun().get_rating_name(most_freq_rating),
            'wins': wins_comp,
            'loses': runs_comp - wins_comp,
            'success_rate': round(wins_comp * 100 / runs_comp, 2),
            'dmg_best': round(runs.aggregate(max_dmg=Max('dmg_total'))['max_dmg']),
            'dmg_avg': round(runs.aggregate(avg_dmg=Avg('dmg_total'))['avg_dmg']),
        }

        # sort descending by 'ranking' formula: win_rate / math.exp((dmg_avg * rating) / -(highest_damage * SSS) )
        # rating - most frequest rating; SSS - 12
        # visualization for highest_damage = 6000000: https://www.wolframalpha.com/input/?i=y%2Fexp%28%28x%29%2F-%286000000%29%29+for+x%3D1..6000000%2C+y%3D0..1
        if record['average_time'] is not None:
            record['sorting_val'] = ((record['success_rate'] / 100) / (math.exp((record['dmg_avg'] * most_freq_rating) / -(highest_damage * 12) )))
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

# dim hole
def get_dimhole_runs_by_comp(comps, dungeon_runs, fastest_run, base=False):
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

        first = runs.first()

        record = {
            'dungeon': first.get_dungeon_display,
            'stage': first.stage,
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

def get_dimhole_runs_per_dungeon(dungeon_runs):
    """Return names, amount of dim hole dungeon types and runs quantity per dungeon."""
    group_by_dungeon = dungeon_runs.values('dungeon').annotate(total=Count('dungeon')).order_by('-total')

    dungeon_name = list()
    dungeon_count = list()

    for group in group_by_dungeon:
        dungeon_name.append(DimensionHoleRun().get_dungeon_name(group['dungeon']))
        dungeon_count.append(group['total'])

    return { 'name': dungeon_name, 'quantity': dungeon_count, 'length': len(dungeon_name) }

def get_dimhole_runs_per_practice(dungeon_runs):
    """Return names, amount of dim hole dungeon types and runs quantity per practice mode."""
    group_by_practice = dungeon_runs.values('practice').annotate(total=Count('practice')).order_by('-total')

    dungeon_name = list()
    dungeon_count = list()

    for group in group_by_practice:
        dungeon_name.append(group['practice'])
        dungeon_count.append(group['total'])

    return { 'name': dungeon_name, 'quantity': dungeon_count, 'length': len(dungeon_name) }

def get_dimhole_runs_per_stage(dungeon_runs):
    """Return names, amount of dim hole dungeon types and runs quantity per stage (difficulty, B1-B5)."""
    group_by_stage = dungeon_runs.values('stage').annotate(total=Count('stage')).order_by('-total')

    dungeon_name = list()
    dungeon_count = list()

    for group in group_by_stage:
        dungeon_name.append(group['stage'])
        dungeon_count.append(group['total'])

    return { 'name': dungeon_name, 'quantity': dungeon_count, 'length': len(dungeon_name) }

# views
@cache_page(CACHE_TTL)
def get_dungeons(request):
    dungeons = DungeonRun.objects.values('dungeon', 'stage', 'win').annotate(avg_time=Avg('clear_time')).annotate(quantity=Count('id')).order_by('dungeon', '-stage', '-win')
    rift_dungeons = RiftDungeonRun.objects.values('dungeon', 'win').annotate(avg_time=Avg('clear_time')).annotate(quantity=Count('dungeon')).order_by('dungeon', '-win')
    dungeons_base = DungeonRun().get_all_dungeons()
    rift_dungeons_base = RiftDungeonRun.get_all_dungeons()

    records = dict()
    for dungeon_base in dungeons_base:
        stages = dict()
        max_stage = 10
        if dungeon_base == 'Rift of Worlds': max_stage = 5
        for i in range(max_stage, 0, -1):
            stages["B" + str(i)] = {
                'avg_time': None,
                'quantity': None,
                'wins': None,
                'loses': None,
            }
        records[dungeon_base] = stages

    for rift_dungeon_base in rift_dungeons_base:
        stages = dict()
        stages["B1"] = {
            'avg_time': None,
            'quantity': None,
            'wins': None,
            'loses': None,
        }
        records[rift_dungeon_base] = stages

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

    for rift_dungeon in rift_dungeons:
        dungeon_name = RiftDungeonRun().get_dungeon_name(rift_dungeon['dungeon'])
        dungeon_stage = "B1"
        dungeon_quantity = rift_dungeon['quantity']

        records[dungeon_name][dungeon_stage] = {
            'avg_time': str(rift_dungeon['avg_time']) if rift_dungeon['avg_time'] else records[dungeon_name][dungeon_stage]['avg_time'],
            'quantity': dungeon_quantity if not records[dungeon_name][dungeon_stage]['quantity'] else records[dungeon_name][dungeon_stage]['quantity'] + dungeon_quantity,
            'wins': dungeon_quantity if rift_dungeon['win'] else records[dungeon_name][dungeon_stage]['wins'],
            'loses': dungeon_quantity if not rift_dungeon['win'] else records[dungeon_name][dungeon_stage]['loses'],
        }

    context = {
        'dungeons': records
    }
    
    return render( request, 'website/dungeons/dungeon_index.html', context)

@cache_page(CACHE_TTL)
def get_dungeon_by_stage(request, name, stage):
    is_filter = False
    filters = list()
    names = name.split('-')

    for i in range(len(names)):
        if names[i] != "of":
            names[i] = names[i].capitalize()
    name = ' '.join(names)

    dungeon_runs = DungeonRun.objects.filter(dungeon=DungeonRun().get_dungeon_id(name), stage=stage).order_by('clear_time')

    if request.GET:
        is_filter = True

    if request.GET.get('base'):
        base = request.GET.get('base').replace('_', ' ')
        filters.append('Base Monster: ' + base)
        dungeon_runs = dungeon_runs.filter(monsters__base_monster__name=base)
        
    dungeon_runs_clear = dungeon_runs.exclude(clear_time__isnull=True).prefetch_related('monsters', 'monsters__base_monster')

    runs_distribution = get_dungeon_runs_distribution(dungeon_runs_clear, 20)
    avg_time = dungeon_runs_clear.aggregate(avg_time=Avg('clear_time'))['avg_time']

    dungeon_runs = dungeon_runs.prefetch_related('monsters', 'monsters__base_monster')

    comps = list()
    for run in dungeon_runs:        
        monsters = list()
        for monster in run.monsters.all():
            monsters.append(monster)
        if monsters not in comps and monsters:
            comps.append(monsters)

    try:
        fastest_run = dungeon_runs_clear.order_by('clear_time').first().clear_time.total_seconds()
    except AttributeError:
        fastest_run = None

    records_personal = sorted(get_dungeon_runs_by_comp(comps, dungeon_runs, fastest_run), key=itemgetter('sorting_val'), reverse = True)
    records_base = sorted(get_dungeon_runs_by_comp(comps, dungeon_runs, fastest_run, True), key=itemgetter('sorting_val'), reverse = True)

    base_names, base_quantities = get_dungeon_runs_by_base_class(dungeon_runs_clear)

    context = {
        # filters
        'is_filter': is_filter,
        'filters': '[' + ', '.join(filters) + ']',

        # all
        'name': name,
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

@cache_page(CACHE_TTL)
def get_rift_dungeon_by_stage(request, name):
    is_filter = False
    filters = list()
    names = name.split('-')

    for i in range(len(names)):
        if names[i] != "of":
            names[i] = names[i].capitalize()
    name = ' '.join(names)

    dungeon_runs = RiftDungeonRun.objects.filter(dungeon=RiftDungeonRun().get_dungeon_id(name)).exclude(clear_rating=None)
    if request.GET:
        is_filter = True

    if request.GET.get('base'):
        base = request.GET.get('base').replace('_', ' ')
        filters.append('Base Monster: ' + base)
        dungeon_runs = dungeon_runs.filter(monsters__base_monster__name=base)


    dungeon_runs = dungeon_runs.prefetch_related('monsters', 'monsters__base_monster')
    dungeon_runs_clear = dungeon_runs.exclude(clear_time__isnull=True)

    damage_distribution = get_rift_dungeon_damage_distribution(dungeon_runs, 20)
    avg_time = dungeon_runs_clear.aggregate(avg_time=Avg('clear_time'))['avg_time']


    comps = list()
    for run in dungeon_runs:
        monsters = list()
        for monster in run.monsters.all():
            monsters.append(monster)
        if monsters not in comps and monsters:
            comps.append(monsters)

    try:
        highest_damage = dungeon_runs.order_by('-dmg_total').first().dmg_total
    except AttributeError:
        highest_damage = None

    records_personal = sorted(get_rift_dungeon_runs_by_comp(comps, dungeon_runs, highest_damage), key=itemgetter('sorting_val'), reverse = True)
    records_base = sorted(get_rift_dungeon_runs_by_comp(comps, dungeon_runs, highest_damage, True), key=itemgetter('sorting_val'), reverse = True)

    base_names, base_quantities = get_dungeon_runs_by_base_class(dungeon_runs)

    context = {
        # filters
        'is_filter': is_filter,
        'filters': '[' + ', '.join(filters) + ']',
    
        # all
        'name': name,
        'dungeon': dungeon_runs, # all runs for given dungeon
        'stage': 1,
        'avg_time': avg_time,
        
        # chart distribution
        'damage_distribution': damage_distribution['distribution'],
        'damage_means': damage_distribution['scope'],
        'damage_colors': create_rgb_colors(damage_distribution['interval']),
    
        # chart base
        'base_names': base_names,
        'base_quantity': base_quantities,
        'base_colors': create_rgb_colors(len(base_names)),
    
        # personal table
        'records_personal': records_personal,
        'records_base': records_base,
    }
    
    return render( request, 'website/dungeons/rift_dungeon_by_stage.html', context)

@cache_page(CACHE_TTL)
def get_dimension_hole(request):
    is_filter = False
    filters = list()

    dungeon_runs = DimensionHoleRun.objects.all().order_by('clear_time')

    if request.GET:
        is_filter = True

    if request.GET.get('base'):
        base = request.GET.get('base').replace('_', ' ')
        filters.append('Base Monster: ' + base)
        dungeon_runs = dungeon_runs.filter(monsters__base_monster__name=base)

    if request.GET.get('dungeon'):
        dungeon = request.GET.get('dungeon').replace('_', ' ')
        filters.append('Dungeon: ' + dungeon)
        dungeon_runs = dungeon_runs.filter(dungeon=DimensionHoleRun().get_dungeon_id_by_name(dungeon))

    if request.GET.get('practice'):
        filters.append('Practice Mode: ' + request.GET.get('practice'))
        dungeon_runs = dungeon_runs.filter(practice=request.GET.get('practice'))

    if request.GET.get('stage'):
        filters.append('Stage: ' + request.GET.get('stage'))
        dungeon_runs = dungeon_runs.filter(stage=request.GET.get('stage'))

    dungeon_runs = dungeon_runs.prefetch_related('monsters', 'monsters__base_monster')
    dungeon_runs_clear = dungeon_runs.exclude(clear_time__isnull=True).prefetch_related('monsters', 'monsters__base_monster')

    runs_distribution = get_dungeon_runs_distribution(dungeon_runs_clear, 20)
    avg_time = dungeon_runs_clear.aggregate(avg_time=Avg('clear_time'))['avg_time']

    comps = list()
    for run in dungeon_runs:
        monsters = list()
        for monster in run.monsters.all():
            monsters.append(monster)
        if monsters not in comps and monsters:
            comps.append(monsters)

    try:
        fastest_run = dungeon_runs_clear.first().clear_time.total_seconds()
    except AttributeError:
        fastest_run = None

    records_personal = sorted(get_dimhole_runs_by_comp(comps, dungeon_runs, fastest_run), key=itemgetter('sorting_val'), reverse = True)
    records_base = sorted(get_dimhole_runs_by_comp(comps, dungeon_runs, fastest_run, True), key=itemgetter('sorting_val'), reverse = True)

    dungeon_runs = dungeon_runs_clear # exclude failed runs
    base_names, base_quantities = get_dungeon_runs_by_base_class(dungeon_runs)
    runs_per_dungeon = get_dimhole_runs_per_dungeon(dungeon_runs)
    runs_per_practice = get_dimhole_runs_per_practice(dungeon_runs)
    runs_per_stage = get_dimhole_runs_per_stage(dungeon_runs)

    context = {
        # filters
        'is_filter': is_filter,
        'filters': '[' + ', '.join(filters) + ']',

        # all
        'dungeon': dungeon_runs, # all runs for given dungeon
        'avg_time': avg_time,
        
        # chart distribution
        'runs_distribution': runs_distribution['distribution'],
        'runs_means': runs_distribution['scope'],
        'runs_colors': create_rgb_colors(runs_distribution['interval']),

        # chart base
        'base_names': base_names,
        'base_quantity': base_quantities,
        'base_colors': create_rgb_colors(len(base_names)),

        # chart dungeon
        'dungeon_names': runs_per_dungeon['name'],
        'dungeon_quantity': runs_per_dungeon['quantity'],
        'dungeon_colors': create_rgb_colors(runs_per_dungeon['length']),

        # chart practice mode
        'practice_names': runs_per_practice['name'],
        'practice_quantity': runs_per_practice['quantity'],
        'practice_colors': create_rgb_colors(runs_per_practice['length']),

        # chart stage
        'stage_names': runs_per_stage['name'],
        'stage_quantity': runs_per_stage['name'],
        'stage_colors': create_rgb_colors(runs_per_stage['length']),

        # personal table
        'records_personal': records_personal,
        'records_base': records_base,
    }

    return render( request, 'website/dimhole/dimhole_index.html', context)
