from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.db.models import F, Q, Avg, Min, Max, Sum, Count, FloatField
from django.template.loader import render_to_string

from website.models import *
from website.tasks import *

import matplotlib.cm as cm
import numpy as np

# deck list w/ filters
def get_deck_list_group_by_family(decks):
    """Return name, amount of families and quantity of monsters for every family in given decks list."""
    family_monsters = dict()
    
    for deck in decks:
        for monster in deck.monsters.all():
            if monster.base_monster.family.name not in family_monsters.keys():
                family_monsters[monster.base_monster.family.name] = 0
            family_monsters[monster.base_monster.family.name] += 1

    family_monsters = {k: family_monsters[k] for k in sorted(family_monsters, key=family_monsters.get, reverse=True)}
    return { 'name': list(family_monsters.keys()), 'quantity': list(family_monsters.values()), 'length': len(family_monsters.keys()) }

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

def get_deck_similar(deck, decks):
    return [temp_deck for temp_deck in decks if temp_deck.place == deck.place and temp_deck.id != deck.id and deck.team_runes_eff - 10 < temp_deck.team_runes_eff and deck.team_runes_eff + 10 > temp_deck.team_runes_eff]

# homunculus
def get_homunculus_builds(homies):
    """Return names, amount of builds and quantity of homunculuses using specific build."""
    group_by_build = homies.values('build').annotate(total=Count('build')).order_by('build')

    build_name = list()
    build_identifier = list()
    build_count = list()

    for group in group_by_build:
        build_name.append(WizardHomunculus.get_build_display(group['build']))
        build_identifier.append(group['build'])
        build_count.append(group['total'])

    return { 'name': build_name, 'quantity': build_count, 'length': len(build_name), 'identifier': build_identifier }

def get_homunculus_skill_description(homunculuses):
    """Return skills & theirs description for specific homie."""
    builds = homunculuses.prefetch_related('build', 'build__depth_1', 'build__depth_2', 'build__depth_3', 'build__depth_4', 'build__depth_5', 'build__homunculus')
    unique_skills = list()

    for homie in builds:
        build = homie.build
        if build.depth_1 not in unique_skills:
            unique_skills.append(build.depth_1)
        if build.depth_2 not in unique_skills:
            unique_skills.append(build.depth_2)
        if build.depth_3 not in unique_skills:
            unique_skills.append(build.depth_3)
        if build.depth_4 not in unique_skills:
            unique_skills.append(build.depth_4)
        if build.depth_5 not in unique_skills:
            unique_skills.append(build.depth_5)
    return unique_skills

# Create your views here.
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
    
    decks = decks.prefetch_related('monsters', 'monsters__base_monster', 'monsters__base_monster__family', 'leader', 'leader__base_monster', 'leader__base_monster__family')
    decks_by_family = get_deck_list_group_by_family(decks)
    decks_by_place = get_deck_list_group_by_place(decks)
    decks_eff = get_deck_list_avg_eff(decks)

    # needs to be last, because it's for TOP table
    amount = min(100, decks.count())
    decks = decks.order_by('-team_runes_eff')[:amount]

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
    deck = get_object_or_404(Deck.objects.prefetch_related('monsters', 'monsters__base_monster', 'monsters__runes__rune_set', 'monsters__runes__equipped_runes', 'monsters__runes__equipped_runes__base_monster', 'monsters__base_monster__family'), id=arg_id)
    decks = Deck.objects.all().order_by('place').prefetch_related('monsters', 'monsters__base_monster', 'leader', 'leader__base_monster')

    context = { 
        'deck': deck,
        'similar': get_deck_similar(deck, decks),
    }

    return render( request, 'website/decks/deck_by_id.html', context)

def get_homunculus(request):
    homunculuses_base = MonsterBase.objects.filter(name__contains='Homunculus', awaken=True)
    homunculuses = WizardHomunculus.objects.all()

    cards = list()
    for homunculus_base in homunculuses_base:
        builds = homunculuses.filter(homunculus__base_monster=homunculus_base).values('build').annotate(Count('id')).order_by()
        cards.append({
            'base_monster': homunculus_base,
            'quantity': homunculuses.filter(homunculus__base_monster=homunculus_base).aggregate(quantity=Count('homunculus__base_monster'))['quantity'],
            'builds': builds,
            'builds_quantity': len(builds),
        })

    context = {
        'cards': cards,

    }

    return render( request, 'website/homunculus/homunculus_index.html', context)

def get_homunculus_base(request, base):
    is_filter = False
    filters = list()
    homunculus_base = MonsterBase.objects.filter(id=base).first()
    homunculuses = WizardHomunculus.objects.filter(homunculus__base_monster__id=base).order_by('-homunculus__base_monster__avg_eff').prefetch_related('build', 'build__depth_1', 'build__depth_2', 'build__depth_3', 'build__depth_4', 'build__depth_5')
    
    if request.GET:
        is_filter = True

    if request.GET.get('build'):
        homunculuses = homunculuses.filter(build=request.GET.get('build'))

    homunculus_skills = get_homunculus_skill_description(homunculuses)

    homunculus_chart_builds = get_homunculus_builds(homunculuses)

    context = {
        'base': homunculus_base,
        'records': homunculuses.prefetch_related('homunculus__base_monster'),

        # chart builds
        'builds_name': homunculus_chart_builds['name'],
        'builds_quantity': homunculus_chart_builds['quantity'],
        'builds_color': create_rgb_colors(homunculus_chart_builds['length']),
        'builds_identifier': homunculus_chart_builds['identifier'],

        # table skills
        'skills': homunculus_skills,
    }

    return render( request, 'website/homunculus/homunculus_base.html', context)

def get_contribute_info(request):
    return render( request, 'website/contribute.html')

def get_credits(request):
    return render( request, 'website/credits.html')
