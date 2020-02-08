from django.shortcuts import get_object_or_404, render
from django.db.models import F, Avg, Min, Max, Sum, Count
from website.models import Wizard, RuneSet, Rune, MonsterFamily, MonsterBase, MonsterSource, Monster, MonsterRep, MonsterHoh, MonsterFusion
import matplotlib.cm as cm
import numpy as np

import json

# Create your views here.
def get_homepage(request):
    runes = Rune.objects.all()
    monsters = Monster.objects.all()
    rune_best = runes.order_by('-efficiency').first()
    rune_equipped = Rune.objects.filter(equipped=True).count()
    monster_best = monsters.order_by('-avg_eff').first()
    monster_cdmg = monsters.order_by('-crit_dmg').first()

    MESSAGES = [
        {
            'id': 1,
            'title': 'Highest rune efficiency',
            'text': f'The most efficient rune stored in database has {rune_best.efficiency if rune_best else 0}% efficiency.',
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
            'arg': monster_best.id if monster_best else 0,
        },
        {
            'id': 4,
            'title': 'Highest critical damage value',
            'text': f'Highest Critical Damage value has {str(monster_cdmg)} with an amazing {monster_cdmg.crit_dmg if monster_cdmg else 0}%',
            'arg': monster_cdmg.id if monster_best else 0,
        },
    ]

    context = {
        'messages': MESSAGES,
    }

    return render( request, 'website/index.html', context )

def get_runes(request):
    runes = Rune.objects.all().order_by('-efficiency')

    avg_eff_above_runes = list()
    avg_eff_below_runes = list()
    avg_eff = runes.aggregate(Avg('efficiency'))['efficiency__avg']

    group_by_set = runes.values('rune_set__name').annotate(total=Count('rune_set')).order_by('-total')
    set_name = list()
    set_count = list()

    for group in group_by_set:
        set_name.append(group['rune_set__name'])
        set_count.append(group['total'])

    set_colors = cm.Dark2(np.linspace(0, 1, len(set_name)))
    set_rgb_colors = [ 'rgba(' + str(int(c[0]*255)) + ', ' + str(int(c[1]*255)) + ', ' + str(int(c[2]*255)) + ', ' + str(.35) + ')' for c in set_colors]

    group_by_slot = runes.values('slot').annotate(total=Count('slot')).order_by('slot')
    slot_number = list()
    slot_count = list()

    for group in group_by_slot:
        slot_number.append(group['slot'])
        slot_count.append(group['total'])

    slot_colors = cm.Dark2(np.linspace(0, 1, len(slot_number)))
    slot_rgb_colors = [ 'rgba(' + str(int(c[0]*255)) + ', ' + str(int(c[1]*255)) + ', ' + str(int(c[2]*255)) + ', ' + str(.35) + ')' for c in slot_colors]



    min_eff = runes.aggregate(Min('efficiency'))['efficiency__min']
    max_eff = runes.aggregate(Max('efficiency'))['efficiency__max']
    rnge = max_eff - min_eff # range

    INTERVALS = 40

    points = [round(min_eff + (max_eff - min_eff) / INTERVALS * i, 2) for i in range(INTERVALS + 1)]
    limits = [[points[i], points[i + 1]] for i in range(INTERVALS)]
    distribution = [0 for _ in range(INTERVALS)]

    for rune in runes:
        for i in range(INTERVALS):
            if i == INTERVALS - 1: # last one, so we need to include max
                if rune.efficiency >= limits[i][0] and rune.efficiency <= limits[i][1]:
                    distribution[i] += 1
                    break
            elif rune.efficiency >= limits[i][0] and rune.efficiency < limits[i][1]:
                    distribution[i] += 1
                    break

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

    best_amount = min(100, runes.count())
    best_runes = runes[:best_amount]

    fastest_runes = runes.order_by(F('sub_speed').desc(nulls_last=True))
    fastest_amount = min(100, fastest_runes.count())
    fastest_runes = fastest_runes[:fastest_amount]

    context = {
        # chart best
        'avg_eff_above_runes': json.dumps(avg_eff_above_runes),
        'avg_eff_above_quantity': len(avg_eff_above_runes),
        'avg_eff_below_runes': json.dumps(avg_eff_below_runes),
        'avg_eff_below_quantity': len(avg_eff_below_runes),
        'avg_eff': round(avg_eff, 2),

        # chart distribution
        'distribution': distribution,
        'means': points,

        # chart group by set
        'set_name': set_name,
        'set_count': set_count,
        'set_color': set_rgb_colors,

        # chart group by slot
        'slot_number': slot_number,
        'slot_count': slot_count,
        'slot_color': slot_rgb_colors,

        # tables
        'best_amount': best_amount,
        'best_runes': best_runes,
        'fastest_runes': fastest_runes,
        'fastest_amount': fastest_amount,
        
    }

    return render( request, 'website/runes/rune_index.html', context)

def get_rune_by_id(request, rune_id):
    rune = get_object_or_404(Rune, id=rune_id)
    context = { 'rune': rune, }

    return render( request, 'website/runes/rune_by_id.html', context )

def get_rune_filter_set(request, set_name):
    runes = Rune.objects.filter(rune_set__name=set_name).order_by('-efficiency')
    context = { 'runes': runes, 'set_name': set_name }

    return render( request, 'website/runes/rune_filter_set.html', context )

def get_rune_filter_slot(request, slot):
    runes = Rune.objects.filter(slot=slot).order_by('-efficiency')
    context = { 'runes': runes, 'slot': slot}

    return render( request, 'website/runes/rune_filter_slot.html', context )