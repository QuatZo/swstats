from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.db.models import F, Q, Avg, Min, Max, Sum, Count, FloatField
from django.template.loader import render_to_string

from website.models import *
from website.tasks import *
from website.functions import *

import matplotlib.cm as cm
import numpy as np
import time
import json

# Create your views here.
def get_homepage(request):
    task = get_homepage_task.delay()

    return render( request, 'website/index.html', {'task_id': task.id})
 
def get_homepage_ajax(request, task_id):
    if request.is_ajax():
        data = get_homepage_task.AsyncResult(task_id) 

        if data.ready():
            context = data.get()
            
            html = render_to_string('website/index_ajax.html', context) # return JSON/Dict like during Desktop Upload
            return HttpResponse(html)

    return HttpResponse('')

def handle_www_profile(request):
    """Return the Compare Page."""
    return render( request, 'website/upload/upload_index.html', {'task_id': None, 'points': get_scoring_system()})

def handle_www_profile_upload(request):
    data = json.loads(request.body)
    if data['command'] != 'HubUserLogin':
        return HttpResponse({'task_id': None})
    task = handle_profile_upload_and_rank_task.delay(data)
    
    return HttpResponse(json.dumps({'task_id': task.id}), content_type="application/json")

def handle_www_profile_upload_ajax(request, task_id):
    if request.is_ajax():
        data = handle_profile_upload_task.AsyncResult(task_id) 

        if data.ready():
            context = data.get()

            for mon in context['comparison']['monsters']:
                mon['obj'] = Monster.objects.get(id=mon['id'])
            for rune in context['comparison']['runes']:
                rune['obj'] = Rune.objects.get(id=rune['id'])

            html = render_to_string('website/upload/upload_ranking.html', context) # return JSON/Dict like during Desktop Upload
            return HttpResponse(html)

    return HttpResponse('')

def get_runes(request):
    task = get_runes_task.delay(dict(request.GET))

    return render( request, 'website/runes/rune_index.html', {'task_id': task.id})

def get_runes_ajax(request, task_id):
    if request.is_ajax():
        data = get_runes_task.AsyncResult(task_id) 

        if data.ready():
            context = data.get()

            context['best_runes'] = Rune.objects.filter(id__in=context['best_runes_ids']).prefetch_related('rune_set', 'equipped_runes', 'equipped_runes__base_monster').order_by('-efficiency')
            context['fastest_runes'] = Rune.objects.filter(id__in=context['fastest_runes_ids']).prefetch_related('rune_set', 'equipped_runes', 'equipped_runes__base_monster').order_by('-sub_speed')

            html = render_to_string('website/runes/rune_index_ajax.html', context) # return JSON/Dict like during Desktop Upload
            return HttpResponse(html)

    return HttpResponse('')

def get_rune_by_id(request, arg_id):
    task = get_rune_by_id_task.delay(dict(request.GET), arg_id)
    rune = get_object_or_404(Rune.objects.prefetch_related('rune_set', 'equipped_runes', 'equipped_runes__base_monster', 'equipped_runes__runes', 'equipped_runes__runes__rune_set' ), id=arg_id)
    
    return render( request, 'website/runes/rune_by_id.html', {'task_id': task.id, 'rune': rune, 'arg_id': arg_id})

def get_rune_by_id_ajax(request, task_id, arg_id):
    if request.is_ajax():
        data = get_rune_by_id_task.AsyncResult(task_id) 

        if data.ready():
            context = data.get()

            context['rune'] = get_object_or_404(Rune.objects.prefetch_related('rune_set', 'equipped_runes', 'equipped_runes__base_monster', 'equipped_runes__runes', 'equipped_runes__runes__rune_set' ), id=arg_id)
            if context['rta_monster_id']:
                context['rta_runes'] = Rune.objects.filter(id__in=RuneRTA.objects.filter(monster__id=context['rta_monster_id']).values_list('rune__id', flat=True))
                context['rta_monster'] = Monster.objects.filter(id=context['rta_monster_id']).prefetch_related('base_monster', 'runes').first()
            else:
                context['rta_runes'] = None
                context['rta_monster'] = None

            context['similar_runes'] = Rune.objects.filter(id__in=context['similar_ids']).order_by('-efficiency').prefetch_related('equipped_runes', 'equipped_runes__base_monster', 'rune_set')

            html = render_to_string('website/runes/rune_by_id_ajax.html', context) # return JSON/Dict like during Desktop Upload
            return HttpResponse(html)

    return HttpResponse('')

def get_artifacts(request):
    task = get_artifacts_task.delay(dict(request.GET))

    return render( request, 'website/artifacts/artifact_index.html', {'task_id': task.id})

def get_artifacts_ajax(request, task_id):
    if request.is_ajax():
        data = get_artifacts_task.AsyncResult(task_id) 

        if data.ready():
            context = data.get()

            context['best_artifacts'] = Artifact.objects.filter(id__in=context['best_artifacts_ids']).order_by('-efficiency')
            
            html = render_to_string('website/artifacts/artifact_index_ajax.html', context) # return JSON/Dict like during Desktop Upload
            return HttpResponse(html)

    return HttpResponse('')

def get_artifact_by_id(request, arg_id):
    task = get_artifact_by_id_task.delay(dict(request.GET), arg_id)
    artifact = get_object_or_404(Artifact.objects.prefetch_related('equipped_artifacts'), id=arg_id)
    
    return render( request, 'website/artifacts/artifact_by_id.html', {'task_id': task.id, 'artifact': artifact, 'arg_id': arg_id})

def get_artifact_by_id_ajax(request, task_id, arg_id):
    if request.is_ajax():
        data = get_artifact_by_id_task.AsyncResult(task_id) 

        if data.ready():
            context = data.get()

            context['artifact'] = get_object_or_404(Artifact.objects.prefetch_related('equipped_artifacts'), id=arg_id)
            context['similar_artifacts'] = Artifact.objects.filter(id__in=context['similar_ids']).order_by('-efficiency').prefetch_related('equipped_artifacts')

            html = render_to_string('website/artifacts/artifact_by_id_ajax.html', context) # return JSON/Dict like during Desktop Upload
            return HttpResponse(html)

    return HttpResponse('')

def get_monsters(request):
    task = get_monsters_task.delay(dict(request.GET))

    return render( request, 'website/monsters/monster_index.html', {'task_id': task.id})

def get_monsters_ajax(request, task_id):
    if request.is_ajax():
        data = get_monsters_task.AsyncResult(task_id) 

        if data.ready():
            context = data.get()

            context['best_monsters'] = Monster.objects.filter(id__in=context['best_monsters_ids']).prefetch_related('base_monster', 'runes', 'runes__rune_set').order_by('-avg_eff')
            context['fastest_monsters'] = Monster.objects.filter(id__in=context['fastest_monsters_ids']).prefetch_related('base_monster', 'runes', 'runes__rune_set').order_by('-speed')
            context['toughest_monsters'] = Monster.objects.filter(id__in=context['toughest_monsters_ids']).prefetch_related('base_monster', 'runes', 'runes__rune_set').order_by('-eff_hp')
            context['toughest_def_break_monsters'] = Monster.objects.filter(id__in=context['toughest_def_break_monsters_ids']).prefetch_related('base_monster', 'runes', 'runes__rune_set').order_by('-eff_hp_def_break')     

            html = render_to_string('website/monsters/monster_index_ajax.html', context) # return JSON/Dict like during Desktop Upload
            return HttpResponse(html)

    return HttpResponse('')

def get_monster_by_id(request, arg_id):
    task = get_monster_by_id_task.delay(dict(request.GET), arg_id)
    monster = get_object_or_404(Monster.objects.prefetch_related('runes', 'runes__rune_set', 'base_monster', 'runes__equipped_runes', 'runes__equipped_runes__base_monster', 'siege_defense_monsters'), id=arg_id)
    
    return render( request, 'website/monsters/monster_by_id.html', {'task_id': task.id, 'monster': monster, 'arg_id': arg_id})

def get_monster_by_id_ajax(request, task_id, arg_id):
    if request.is_ajax():
        data = get_monster_by_id_task.AsyncResult(task_id) 

        if data.ready():
            context = data.get()

            context['monster'] = get_object_or_404(Monster.objects.prefetch_related('runes', 'runes__rune_set', 'base_monster', 'runes__equipped_runes', 'runes__equipped_runes__base_monster', 'siege_defense_monsters'), id=arg_id)
            context['rta']['build'] = Rune.objects.filter(id__in=context['rta']['build_ids'])
            context['similar'] = Monster.objects.filter(id__in=context['similar_ids']).prefetch_related('runes', 'runes__rune_set', 'base_monster', 'base_monster__family')
            context['rta_similar'] = dict()
            for rta_sim_mon_id, rta_sim_rune_id in context['rta_similar_ids'].items():
                context['rta_similar'][Monster.objects.get(id=rta_sim_mon_id)] = Rune.objects.filter(id__in=rta_sim_rune_id)
            context['decks'] = Deck.objects.filter(id__in=context['decks_ids']).prefetch_related('monsters', 'monsters__base_monster', 'leader', 'leader__base_monster')
            context['records'] = get_monster_records(context['monster'])

            html = render_to_string('website/monsters/monster_by_id_ajax.html', context)
            return HttpResponse(html)

    return HttpResponse('')

def get_decks(request):
    task = get_decks_task.delay(dict(request.GET))

    return render( request, 'website/decks/deck_index.html', {'task_id': task.id})

def get_decks_ajax(request, task_id):
    if request.is_ajax():
        data = get_decks_task.AsyncResult(task_id) 

        if data.ready():
            context = data.get()

            context['decks'] = Deck.objects.filter(id__in=context['decks_ids']).prefetch_related('monsters', 'monsters__base_monster', 'monsters__base_monster__family', 'leader', 'leader__base_monster', 'leader__base_monster__family').order_by('-team_runes_eff')

            html = render_to_string('website/decks/deck_index_ajax.html', context) # return JSON/Dict like during Desktop Upload
            return HttpResponse(html)

    return HttpResponse('')

def get_deck_by_id(request, arg_id):
    task = get_deck_by_id_task.delay(dict(request.GET))
    deck = get_object_or_404(Deck.objects.prefetch_related('monsters', 'monsters__base_monster', 'monsters__runes__rune_set', 'monsters__runes__equipped_runes', 'monsters__runes__equipped_runes__base_monster', 'monsters__base_monster__family'), id=arg_id)
            
    return render( request, 'website/decks/deck_by_id.html', {'task_id': task.id, 'deck': deck, 'arg_id': arg_id})

def get_deck_by_id_ajax(request, task_id, arg_id):
    if request.is_ajax():
        data = get_deck_by_id_task.AsyncResult(task_id) 

        if data.ready():
            deck = get_object_or_404(Deck.objects.prefetch_related('monsters', 'monsters__base_monster', 'monsters__runes__rune_set', 'monsters__runes__equipped_runes', 'monsters__runes__equipped_runes__base_monster', 'monsters__base_monster__family'), id=arg_id)
            decks = Deck.objects.all().order_by('place').prefetch_related('monsters', 'monsters__base_monster', 'leader', 'leader__base_monster')

            context = { 
                'deck': deck,
                'similar': get_deck_similar(deck, decks),
                'arg_id': arg_id,
            }

            html = render_to_string('website/decks/deck_by_id_ajax.html', context) # return JSON/Dict like during Desktop Upload
            return HttpResponse(html)

    return HttpResponse('')

def get_siege_records(request):
    task = get_siege_records_task.delay(dict(request.GET))

    return render( request, 'website/siege/siege_index.html', {'task_id': task.id})

def get_siege_records_ajax(request, task_id):
    if request.is_ajax():
        data = get_siege_records_task.AsyncResult(task_id) 

        if data.ready():
            context = data.get()
            context['best_records'] = SiegeRecord.objects.filter(id__in=context['records_ids']).prefetch_related('monsters', 'monsters__base_monster', 'wizard', 'wizard__guild', 'leader', 'leader__base_monster', 'monsters__base_monster__family').annotate(sorting_val=Sum((F('win') + 250) * F('ratio'), output_field=FloatField())).order_by('-sorting_val')[:context['best_amount']]

            html = render_to_string('website/siege/siege_index_ajax.html', context) # return JSON/Dict like during Desktop Upload
            return HttpResponse(html)

    return HttpResponse('')

def get_dungeons(request):
    dungeons = DungeonRun.objects.values('dungeon', 'stage', 'win').annotate(avg_time=Avg('clear_time')).annotate(quantity=Count('id')).order_by('dungeon', '-stage', '-win')
    rift_dungeons = RiftDungeonRun.objects.values('dungeon', 'win').annotate(avg_time=Avg('clear_time')).annotate(quantity=Count('dungeon')).order_by('dungeon', '-win')
    dungeons_base = DungeonRun().get_all_dungeons()
    rift_dungeons_base = RiftDungeonRun.get_all_dungeons()
    raid_dungeons = RaidDungeonRun.objects.values('stage', 'win').annotate(avg_time=Avg('clear_time')).annotate(quantity=Count('stage')).order_by('-stage')
    raid_dungeon_name = 'Rift of Worlds'


    records = dict()
    for dungeon_base in dungeons_base:
        stages = dict()
        max_stage = 12 if DungeonRun().get_dungeon_id(dungeon_base) in [6001, 8001, 9001] else 10
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
    
    
    raid_max_stage = 5
    stages = dict()
    for i in range(raid_max_stage, 0, -1):
        stages["B" + str(i)] = {
            'avg_time': None,
            'quantity': None,
            'wins': None,
            'loses': None,
        }
    records[raid_dungeon_name] = stages

    for dungeon in dungeons:
        dungeon_name = DungeonRun().get_dungeon_name(dungeon['dungeon'])
        if not dungeon_name:
            continue
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
        if not dungeon_name:
            continue
        dungeon_stage = "B1"
        dungeon_quantity = rift_dungeon['quantity']

        records[dungeon_name][dungeon_stage] = {
            'avg_time': str(rift_dungeon['avg_time']) if rift_dungeon['avg_time'] else records[dungeon_name][dungeon_stage]['avg_time'],
            'quantity': dungeon_quantity if not records[dungeon_name][dungeon_stage]['quantity'] else records[dungeon_name][dungeon_stage]['quantity'] + dungeon_quantity,
            'wins': dungeon_quantity if rift_dungeon['win'] else records[dungeon_name][dungeon_stage]['wins'],
            'loses': dungeon_quantity if not rift_dungeon['win'] else records[dungeon_name][dungeon_stage]['loses'],
        }

    for raid_dungeon in raid_dungeons:
        dungeon_stage = "B" + str(raid_dungeon['stage'])
        dungeon_quantity = raid_dungeon['quantity']

        records[raid_dungeon_name][dungeon_stage] = {
            'avg_time': str(raid_dungeon['avg_time']) if raid_dungeon['avg_time'] else records[raid_dungeon_name][dungeon_stage]['avg_time'],
            'quantity': dungeon_quantity if not records[raid_dungeon_name][dungeon_stage]['quantity'] else records[raid_dungeon_name][dungeon_stage]['quantity'] + dungeon_quantity,
            'wins': dungeon_quantity if raid_dungeon['win'] else records[raid_dungeon_name][dungeon_stage]['wins'],
            'loses': dungeon_quantity if not raid_dungeon['win'] else records[raid_dungeon_name][dungeon_stage]['loses'],
        }

    context = {
        'dungeons': records
    }
    
    return render( request, 'website/dungeons/dungeon_index.html', context)

def get_dungeon_by_stage(request, name, stage):
    if name.lower() == 'rift-of-worlds':
        task = get_raid_dungeon_by_stage_task.delay(dict(request.GET), stage)
    else:
        task = get_dungeon_by_stage_task.delay(dict(request.GET), name, stage)
    
    return render( request, 'website/dungeons/dungeon_by_stage.html', {'task_id': task.id, 'name': name.capitalize().replace('_', ' ').replace('-', ' '), 'stage': stage})

def get_dungeon_by_stage_ajax(request, task_id, name, stage):
    if request.is_ajax():
        if name.lower() == 'rift of worlds':
            data = get_raid_dungeon_by_stage_task.AsyncResult(task_id)

            if data.ready():
                context = data.get()

                for record in context['records_personal']:
                    record['frontline'] = [Monster.objects.get(id=monster_id) if monster_id else None for monster_id in record['frontline']]
                    record['backline'] = [Monster.objects.get(id=monster_id) if monster_id else None for monster_id in record['backline']]
                    record['leader'] = Monster.objects.get(id=record['leader']) if record['leader'] else None

                html = render_to_string('website/dungeons/raid_dungeon_by_stage_ajax.html', context) # return JSON/Dict like during Desktop Upload
                return HttpResponse(html)
        else:
            data = get_dungeon_by_stage_task.AsyncResult(task_id) 

            if data.ready():
                context = data.get()

                for record in context['records_personal']:
                    record['comp'] = [Monster.objects.get(id=monster_id) for monster_id in record['comp']]

                html = render_to_string('website/dungeons/dungeon_by_stage_ajax.html', context) # return JSON/Dict like during Desktop Upload
                return HttpResponse(html)

    return HttpResponse('')

def get_rift_dungeon_by_stage(request, name):
    task = get_rift_dungeon_by_stage_task.delay(dict(request.GET), name)
    
    return render( request, 'website/dungeons/rift_dungeon_by_stage.html', {'task_id': task.id, 'name': name.capitalize().replace('_', ' ').replace('-', ' ')})

def get_rift_dungeon_by_stage_ajax(request, task_id, name):
    if request.is_ajax():
        data = get_rift_dungeon_by_stage_task.AsyncResult(task_id) 

        if data.ready():
            context = data.get()
            
            for record in context['records_personal']:
                record['frontline'] = [Monster.objects.get(id=monster_id) if monster_id else None for monster_id in record['frontline']]
                record['backline'] = [Monster.objects.get(id=monster_id) if monster_id else None for monster_id in record['backline']]
                record['leader'] = Monster.objects.get(id=record['leader']) if record['leader'] else None

            html = render_to_string('website/dungeons/rift_dungeon_by_stage_ajax.html', context) # return JSON/Dict like during Desktop Upload
            return HttpResponse(html)

    return HttpResponse('')

def get_dimension_hole(request):
    task = get_dimension_hole_task.delay(dict(request.GET))

    return render( request, 'website/dimhole/dimhole_index.html', {'task_id': task.id})

def get_dimension_hole_ajax(request, task_id):
    if request.is_ajax():
        data = get_dimension_hole_task.AsyncResult(task_id) 

        if data.ready():
            context = data.get()
            
            if context['records_ok']:
                for record in context['records_personal']:
                    record['comp'] = [Monster.objects.get(id=monster_id) for monster_id in record['comp']]

            html = render_to_string('website/dimhole/dimhole_index_ajax.html', context) # return JSON/Dict like during Desktop Upload
            return HttpResponse(html)

    return HttpResponse('')

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
    homunculus_base = MonsterBase.objects.get(id=base)
    task = get_homunculus_base_task.delay(dict(request.GET), base)

    return render( request, 'website/homunculus/homunculus_base.html', {'task_id': task.id, 'base': homunculus_base})

def get_homunculus_base_ajax(request, task_id, base):
    if request.is_ajax():
        data = get_homunculus_base_task.AsyncResult(task_id) 

        if data.ready():
            context = data.get()

            context['records'] = WizardHomunculus.objects.filter(id__in=context['records_ids']).prefetch_related('homunculus__base_monster').order_by('-homunculus__avg_eff')
            context['skills'] = HomunculusSkill.objects.filter(id__in=context['skills_ids'])

            html = render_to_string('website/homunculus/homunculus_base_ajax.html', context) # return JSON/Dict like during Desktop Upload
            return HttpResponse(html)

    return HttpResponse('')

def get_contribute_info(request):
    return render( request, 'website/contribute.html')

def get_credits(request):
    return render( request, 'website/credits.html')
