from django.shortcuts import get_object_or_404, render
from django.db.models import F, Avg, Min, Max, Sum, Count
from django.utils.encoding import force_text
from website.models import RuneSet, Rune, Monster

import matplotlib.cm as cm
import numpy as np


def get_homepage(request):
    """Return the homepage with carousel messages & introduction."""
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

def create_rgb_colors(length):
    """Return the array of 'length', which contains 'rgba(r, g, b, a)' strings for Chart.js."""
    return [ 'rgba(' + str(int(c[0]*255)) + ', ' + str(int(c[1]*255)) + ', ' + str(int(c[2]*255)) + ', ' + str(.35) + ')' for c in cm.rainbow(np.linspace(0, 1, length))]

def get_rune_list_avg_eff(runes):
    """Return the avg efficiency of given runes, incl. these runes splitted into two sets (above & equal, below)."""
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


# Create your views here.
def get_runes(request):
    runes = Rune.objects.all().order_by('-efficiency')    

    avg_eff_runes = get_rune_list_avg_eff(runes)
    normal_distribution_runes = get_rune_list_normal_distribution(runes, 40)
    runes_by_set = get_rune_list_grouped_by_set(runes)
    runes_by_slot = get_rune_list_grouped_by_slot(runes)
    runes_by_quality = get_rune_list_grouped_by_quality(runes)
    best_runes = get_rune_list_best(runes, 100)
    fastest_runes = get_rune_list_fastest(runes, 100)

    context = {
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

        # table best by efficiency
        'best_runes': best_runes,
        'best_amount': len(best_runes),

        # table best by speed
        'fastest_runes': fastest_runes,
        'fastest_amount': len(fastest_runes),
    }

    return render( request, 'website/runes/rune_index.html', context)

def get_rune_by_id(request, rune_id):
    rune = get_object_or_404(Rune, id=rune_id)
    context = { 'rune': rune, }

    return render( request, 'website/runes/rune_by_id.html', context )

def get_rune_filter_set(request, set_name):
    runes = Rune.objects.filter(rune_set__name=set_name).order_by('-efficiency')

    avg_eff_runes = get_rune_list_avg_eff(runes)
    normal_distribution_runes = get_rune_list_normal_distribution(runes, 20)
    runes_by_quality = get_rune_list_grouped_by_quality(runes)
    runes_by_slot = get_rune_list_grouped_by_slot(runes)
    best_runes = get_rune_list_best(runes, 100)
    fastest_runes = get_rune_list_fastest(runes, 100)

    context = {
        'set': set_name,

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

        # chart group by quality
        'quality_name': runes_by_quality['name'],
        'quality_count': runes_by_quality['quantity'],
        'quality_color': create_rgb_colors(runes_by_quality['length']),

        # chart group by slot
        'slot_number': runes_by_slot['number'],
        'slot_count': runes_by_slot['quantity'],
        'slot_color': create_rgb_colors(runes_by_slot['length']),

        # table best by efficiency
        'best_runes': best_runes,
        'best_amount': len(best_runes),

        # table best by speed
        'fastest_runes': fastest_runes,
        'fastest_amount': len(fastest_runes),
    }

    return render( request, 'website/runes/rune_filter_set.html', context )

def get_rune_filter_slot(request, slot):
    runes = Rune.objects.filter(slot=slot).order_by('-efficiency')

    avg_eff_runes = get_rune_list_avg_eff(runes)
    normal_distribution_runes = get_rune_list_normal_distribution(runes, 20)
    runes_by_set = get_rune_list_grouped_by_set(runes)
    runes_by_quality = get_rune_list_grouped_by_quality(runes)
    best_runes = get_rune_list_best(runes, 100)
    fastest_runes = get_rune_list_fastest(runes, 100)

    context = {
        'slot': slot,

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

        # chart group by quality
        'quality_name': runes_by_quality['name'],
        'quality_count': runes_by_quality['quantity'],
        'quality_color': create_rgb_colors(runes_by_quality['length']),

        # table best by efficiency
        'best_runes': best_runes,
        'best_amount': len(best_runes),

        # table best by speed
        'fastest_runes': fastest_runes,
        'fastest_amount': len(fastest_runes),
    }

    return render( request, 'website/runes/rune_filter_slot.html', context )

def get_rune_filter_quality(request, quality):
    quality_id = Rune().get_rune_quality_id(quality)
    runes = Rune.objects.filter(quality=quality_id).order_by('-efficiency')    

    avg_eff_runes = get_rune_list_avg_eff(runes)
    normal_distribution_runes = get_rune_list_normal_distribution(runes, 40)
    runes_by_set = get_rune_list_grouped_by_set(runes)
    runes_by_slot = get_rune_list_grouped_by_slot(runes)
    runes_by_quality = get_rune_list_grouped_by_quality(runes)
    best_runes = get_rune_list_best(runes, 100)
    fastest_runes = get_rune_list_fastest(runes, 100)

    context = {
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

        # table best by efficiency
        'best_runes': best_runes,
        'best_amount': len(best_runes),

        # table best by speed
        'fastest_runes': fastest_runes,
        'fastest_amount': len(fastest_runes),
    }

    return render( request, 'website/runes/rune_filter_quality.html', context)



