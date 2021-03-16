from django.shortcuts import render
from django.conf import settings
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from celery.result import AsyncResult
from website.celery import app as celery_app

from swstats_web.permissions import IsSwstatsWeb

from website.models import Monster, Rune, Artifact, DungeonRun, DimensionHoleRun, RiftDungeonRun, RaidDungeonRun
from .tasks import *
from .functions import get_scoring_system, get_runes_table, get_monsters_table, get_artifacts_table, get_siege_table, calculate_cache_key
from .serializers import MonsterSerializer, RuneSerializer, ArtifactSerializer

import json
import itertools
from datetime import timedelta, datetime
import os
from operator import itemgetter

from rest_framework_extensions.cache.decorators import (
    cache_response
)
# Create your views here.


class HomepageView(APIView):
    permission_classes = [IsSwstatsWeb, ]
    swagger_schema = None

    @cache_response(60 * 15, key_func=calculate_cache_key, cache_errors=False)
    def get(self, request, format=None):
        cards = [
            {
                "id": 1,
                "animated": False,
                "format": "string",
                "w": 3,  # 1-12, card width
                "title": "Introduction",
                "desc": "Summoners War Statistics Web is a website which stores, analyse and shows in a friendly way contributors data but also implements the most important features from Summoners War Statistics Windows App which had been discontinued because of technology limits.",
            },
            {
                "id": 2,
                "animated": False,
                "format": "string",
                "w": 3,  # 1-12, card width
                "title": "Data Logs",
                "desc": "In Data Logs Section you can find analysis, charts, tables and reports based on Contributors data. Every data used in Data Logs Section is being collected annonymously by using website built-in Upload Functionality (together with Rank & Compare) or by using SWEX Plugin. More information in Contribute page.",
            },
            {
                "id": 3,
                "animated": False,
                "format": "string",
                "w": 3,
                "title": "Personal",
                "desc": "In Personal Section you can find interactive towers & flags calculator. If you don't want to type everything by yourself, you can upload JSON profile. Doing this, you won't upload your profile to the website. Whole calculator works locally in your browser.",
            },
            {
                "id": 4,
                "animated": False,
                "format": "string",
                "w": 3,
                "title": "I don't want my data to be here",
                "desc": "I can assure you that no user will be able to tell if specific monster, rune, artifact or dungeon run is yours or not. However, if you want your data to be deleted, please contact me through Reddit and we will see what can be done. Be prepare to give me JSON file, in order to blacklist it."
            },
            {
                "id": 5,
                "animated": True,
                "format": "number",
                "precision": 0,
                "w": 2,
                "title": "Monsters",
                "desc": Monster.objects.all().count(),
            },
            {
                "id": 6,
                "animated": True,
                "format": "number",
                "precision": 0,
                "w": 2,
                "title": "Runes",
                "desc": Rune.objects.all().count(),
            },
            {
                "id": 7,
                "animated": True,
                "format": "number",
                "precision": 0,
                "w": 2,
                "title": "Artifacts",
                "desc": Artifact.objects.all().count(),
            },
            {
                "id": 8,
                "animated": True,
                "format": "percentage",
                "precision": 2,
                "w": 3,
                "title": "Most Efficient Rune",
                "desc": Rune.objects.order_by('-efficiency').first().efficiency,
            },
            {
                "id": 9,
                "animated": True,
                "format": "percentage",
                "precision": 0,
                "w": 3,
                "title": "Highest Crit Damage",
                "desc": Monster.objects.order_by('-crit_dmg').first().crit_dmg,
            },
            {
                "id": 10,
                "animated": True,
                "format": "number",
                "precision": 0,
                "w": 2,
                "title": "Highest Speed",
                "desc": Monster.objects.order_by('-speed').first().speed,
            },
            {
                "id": 11,
                "animated": True,
                "format": "seconds",
                "precision": 0,
                "w": 2,
                "title": "Fastest GB12",
                "desc": DungeonRun.objects.filter(win=True, dungeon=8001, stage=12).order_by('clear_time').first().clear_time.total_seconds(),
            },
            {
                "id": 12,
                "animated": True,
                "format": "seconds",
                "precision": 0,
                "w": 2,
                "title": "Fastest DB12",
                "desc": DungeonRun.objects.filter(win=True, dungeon=9001, stage=12).order_by('clear_time').first().clear_time.total_seconds(),
            },
            {
                "id": 13,
                "animated": True,
                "format": "seconds",
                "precision": 0,
                "w": 2,
                "title": "Fastest NB12",
                "desc": DungeonRun.objects.filter(win=True, dungeon=6001, stage=12).order_by('clear_time').first().clear_time.total_seconds(),
            },
            {
                "id": 14,
                "animated": True,
                "format": "seconds",
                "precision": 0,
                "w": 2,
                "title": "Fastest SB10",
                "desc": DungeonRun.objects.filter(win=True, dungeon=9501, stage=10).order_by('clear_time').first().clear_time.total_seconds(),
            },
            {
                "id": 15,
                "animated": True,
                "format": "seconds",
                "precision": 0,
                "w": 2,
                "title": "Fastest PB10",
                "desc": DungeonRun.objects.filter(win=True, dungeon=9502, stage=10).order_by('clear_time').first().clear_time.total_seconds(),
            },
        ]

        return Response(cards)


class ScoringView(APIView):
    permission_classes = [IsSwstatsWeb, ]
    swagger_schema = None

    def get(self, request, format=None):
        return Response({'points': get_scoring_system(), 'comparison': {}})


class UploadView(APIView):
    permission_classes = [IsSwstatsWeb, ]
    swagger_schema = None

    def post(self, request, format=None):
        data = json.loads(request.body)
        if data['command'] != 'HubUserLogin':
            return Response({'error': 'Invalid JSON File'}, status=status.HTTP_400_BAD_REQUEST)

        task = handle_profile_upload_and_rank_task.delay(data)

        return Response({'status': task.state, 'task_id': task.id})


class RunesView(APIView):
    permission_classes = [IsSwstatsWeb, ]
    swagger_schema = None

    @cache_response(60 * 15, key_func=calculate_cache_key, cache_errors=False)
    def get(self, request, format=None):
        task = fetch_runes_data.delay(list(request.GET.lists()))

        return Response({'status': task.state, 'task_id': task.id})


class RunesTableView(APIView):
    permission_classes = [IsSwstatsWeb, ]
    swagger_schema = None

    @cache_response(60 * 15, key_func=calculate_cache_key, cache_errors=False)
    def get(self, request, format=None):
        runes_table = get_runes_table(request)
        if 'error' in runes_table:
            return Response(runes_table, status=status.HTTP_400_BAD_REQUEST)
        return Response(runes_table)


class MonstersView(APIView):
    permission_classes = [IsSwstatsWeb, ]
    swagger_schema = None

    @cache_response(60 * 15, key_func=calculate_cache_key, cache_errors=False)
    def get(self, request, format=None):
        task = fetch_monsters_data.delay(list(request.GET.lists()))

        return Response({'status': task.state, 'task_id': task.id})


class MonstersTableView(APIView):
    permission_classes = [IsSwstatsWeb, ]
    swagger_schema = None

    @cache_response(60 * 15, key_func=calculate_cache_key, cache_errors=False)
    def get(self, request, format=None):
        monsters_table = get_monsters_table(request)
        if 'error' in monsters_table:
            return Response(monsters_table, status=status.HTTP_400_BAD_REQUEST)
        return Response(monsters_table)


class ArtifactsView(APIView):
    permission_classes = [IsSwstatsWeb, ]
    swagger_schema = None

    @cache_response(60 * 15, key_func=calculate_cache_key, cache_errors=False)
    def get(self, request, format=None):
        task = fetch_artifacts_data.delay(list(request.GET.lists()))

        return Response({'status': task.state, 'task_id': task.id})


class ArtifactsTableView(APIView):
    permission_classes = [IsSwstatsWeb, ]
    swagger_schema = None

    @cache_response(60 * 15, key_func=calculate_cache_key, cache_errors=False)
    def get(self, request, format=None):
        artifacts_table = get_artifacts_table(request)
        if 'error' in artifacts_table:
            return Response(artifacts_table, status=status.HTTP_400_BAD_REQUEST)
        return Response(artifacts_table)


class SiegeView(APIView):
    permission_classes = [IsSwstatsWeb, ]
    swagger_schema = None

    @cache_response(60 * 15, key_func=calculate_cache_key, cache_errors=False)
    def get(self, request, format=None):
        task = fetch_siege_data.delay(list(request.GET.lists()))

        return Response({'status': task.state, 'task_id': task.id})


class SiegeTableView(APIView):
    permission_classes = [IsSwstatsWeb, ]
    swagger_schema = None

    @cache_response(60 * 15, key_func=calculate_cache_key, cache_errors=False)
    def get(self, request, format=None):
        siege_table = get_siege_table(request)
        if 'error' in siege_table:
            return Response(siege_table, status=status.HTTP_400_BAD_REQUEST)
        return Response(siege_table)


class CairosView(APIView):
    permission_classes = [IsSwstatsWeb, ]
    swagger_schema = None

    @cache_response(60 * 15, key_func=calculate_cache_key, cache_errors=False)
    def get(self, request, format=None):
        dungeon_runs = DungeonRun.objects.defer('wizard', 'monsters', 'date').order_by(
            'dungeon', '-stage', '-win').values('dungeon', 'stage', 'clear_time', 'win')
        dungeons = {}

        for id_, name in DungeonRun.DUNGEON_TYPES:
            dungeons[id_] = {
                'id': id_,
                'name': name,
                'path': name.replace('\'', '').replace(' ', '_').lower(),
                'image': 'https://swstats.info/static/website/images/dungeons/dungeon_' + name.replace('\'', '').replace(' ', '_').lower() + '.png',
                'stages': [],
            }

        for d_id, d_id_group in itertools.groupby(dungeon_runs, lambda item: item['dungeon']):
            if d_id not in dungeons:
                continue  # Secret Dungeon
            d_g_id = list(d_id_group)
            max_stage = d_g_id[0]['stage']
            dungeons[d_id]['stages'] = [{
                'stage': stage,
                'records': 0,
                'avg_time': 0,
                'wins': 0,
            } for stage in range(max_stage, 0, -1)]

            for d_s, d_s_group in itertools.groupby(d_g_id, lambda item: item['stage']):
                d_g_s = list(d_s_group)
                dungeons[d_id]['stages'][max_stage -
                                         d_s]['records'] = len(d_g_s)

                for _, d_w_group in itertools.groupby(d_g_s, lambda item: item['win']):
                    d_g_w = list(d_w_group)
                    if d_g_w[0]['win'] == False:
                        break
                    wins = len(d_g_w)
                    dungeons[d_id]['stages'][max_stage - d_s]['wins'] = wins
                    clear_times = [d['clear_time'] for d in d_g_w]
                    avg_time = sum(
                        clear_times, timedelta(0)) / len(clear_times)
                    avg_str = str(avg_time)
                    try:
                        avg_index = avg_str.index('.')
                        avg_str = avg_str[:avg_index]
                    except ValueError:
                        pass
                    dungeons[d_id]['stages'][max_stage -
                                             d_s]['avg_time'] = avg_str

        return Response(list(dungeons.values()))


class CairosDetailView(APIView):
    permission_classes = [IsSwstatsWeb, ]
    swagger_schema = None

    @cache_response(60 * 15, key_func=calculate_cache_key, cache_errors=False)
    def get(self, request, format=None):
        if 'cid' not in request.GET or 'stage' not in request.GET:
            return Response({}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            cid = request.GET['cid'].split('-')

            if not cid or len(cid) > 2:
                raise ValueError(f"Wrong Cairos ID: {request.GET['cid']}")

            cid = int(cid[0])
            stage = int(request.GET['stage'])

            if cid not in [d[0] for d in DungeonRun.DUNGEON_TYPES]:
                raise ValueError(
                    f"Non existing Cairos ID: {request.GET['cid']}")

            task = fetch_cairos_detail_data.delay(
                list(request.GET.lists()), cid, stage)

            return Response({'status': task.state, 'task_id': task.id})
        except ValueError:
            return Response({}, status=status.HTTP_401_UNAUTHORIZED)


class RiftView(APIView):
    permission_classes = [IsSwstatsWeb, ]
    swagger_schema = None

    @cache_response(60 * 15, key_func=calculate_cache_key, cache_errors=False)
    def get(self, request, format=None):
        raid_recs = RaidDungeonRun.objects.only(
            'stage', 'win', 'clear_time').order_by('-stage', '-win')
        raid_stages = []
        for s, r in itertools.groupby(raid_recs, lambda item: item.stage):
            r_r = list(r)
            for _, r_w in itertools.groupby(r_r, lambda item: item.win):
                r_r_w = [r_ for r_ in list(r_w) if r_.win is not None]
                if not r_r_w or r_r_w[0].win == False:
                    continue
                wins = len(r_r_w)
                clear_times = [d.clear_time for d in r_r_w]
                avg_time = sum(clear_times, timedelta(0)) / len(clear_times)
                avg_str = str(avg_time)
                try:
                    avg_index = avg_str.index('.')
                    avg_str = avg_str[:avg_index]
                except ValueError:
                    pass
                raid_stages.append({
                    'stage': s,
                    'records': len(r_r),
                    'avg_time': avg_str,
                    'wins': wins,
                })

        dungeons = {
            1: {
                'id': 1,
                'name': 'Rift of Worlds',
                'path': 'rift_of_worlds',
                'image': 'https://swstats.info/static/website/images/dungeons/dungeon_rift_of_worlds.png',
                'stages': raid_stages,
            },
        }

        dungeon_runs = RiftDungeonRun.objects.only('dungeon', 'clear_rating', 'dmg_total', ).order_by(
            'dungeon', '-clear_rating').values('dungeon', 'clear_rating', 'dmg_total')

        for id_, name in RiftDungeonRun.DUNGEON_TYPES:
            dungeons[id_] = {
                'id': id_,
                'name': name,
                'path': name.replace('\'', '').replace(' ', '_').lower(),
                'image': 'https://swstats.info/static/website/images/dungeons/dungeon_' + name.replace('\'', '').replace(' ', '_').lower() + '.png',
                'stages': [],
            }

        for d_id, d_id_group in itertools.groupby(dungeon_runs, lambda item: item['dungeon']):
            if d_id not in dungeons:
                continue  # dont know, something new
            d_g_id = list(d_id_group)
            dungeons[d_id]['stages'] = [{
                'stage': 1,
                'records': len(d_g_id),
                'avg_dmg': round(sum(d['dmg_total'] for d in d_g_id) / len(d_g_id)),
                'sss': 0,
            }]

            for d_s, d_s_group in itertools.groupby(d_g_id, lambda item: item['clear_rating']):
                if not d_s:
                    continue
                if d_s != 12:
                    break  # only SSS
                d_g_s = list(d_s_group)
                dungeons[d_id]['stages'][0]['sss'] = len(d_g_s)

        return Response(list(dungeons.values()))


class RiftDetailView(APIView):
    permission_classes = [IsSwstatsWeb, ]
    swagger_schema = None

    @cache_response(60 * 15, key_func=calculate_cache_key, cache_errors=False)
    def get(self, request, format=None):
        if 'cid' not in request.GET or 'stage' not in request.GET:
            return Response({}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            cid = request.GET['cid'].split('-')

            if not cid or len(cid) > 2:
                raise ValueError(f"Wrong Cairos ID: {request.GET['cid']}")

            cid = int(cid[0])
            stage = int(request.GET['stage'])

            if cid not in [d[0] for d in DungeonRun.DUNGEON_TYPES] and cid != 1:
                raise ValueError(
                    f"Non existing Cairos ID: {request.GET['cid']}")

            if cid == 1:
                task = fetch_raid_detail_data.delay(
                    list(request.GET.lists()), stage)
            else:
                task = fetch_rift_detail_data.delay(
                    list(request.GET.lists()), cid)

            return Response({'status': task.state, 'task_id': task.id})
        except ValueError:
            return Response({}, status=status.HTTP_401_UNAUTHORIZED)


class DimholeView(APIView):
    permission_classes = [IsSwstatsWeb, ]
    swagger_schema = None

    @cache_response(60 * 15, key_func=calculate_cache_key, cache_errors=False)
    def get(self, request, format=None):
        dungeon_runs = DimensionHoleRun.objects.defer('wizard', 'monsters', 'date').order_by(
            'dungeon', '-stage', '-win').values('dungeon', 'stage', 'clear_time', 'win')
        dungeons = {}

        for id_, name in DimensionHoleRun.DIM_HOLE_TYPES:
            dungeons[id_] = {
                'id': id_,
                'name': name,
                'path': name.replace('\'', '').replace(' ', '_').lower(),
                'image': 'https://swstats.info/static/website/images/dungeons/dimhole_' + name.replace('\'', '').replace(' ', '_').replace('(', '').replace(')', '').lower() + '.png',
                'stages': [],
            }

        for d_id, d_id_group in itertools.groupby(dungeon_runs, lambda item: item['dungeon']):
            if d_id not in dungeons:
                continue  # Predator
            d_g_id = list(d_id_group)
            max_stage = d_g_id[0]['stage']
            dungeons[d_id]['stages'] = [{
                'stage': stage,
                'records': 0,
                'avg_time': 0,
                'wins': 0,
            } for stage in range(max_stage, 0, -1)]

            for d_s, d_s_group in itertools.groupby(d_g_id, lambda item: item['stage']):
                d_g_s = list(d_s_group)
                dungeons[d_id]['stages'][max_stage -
                                         d_s]['records'] = len(d_g_s)

                for _, d_w_group in itertools.groupby(d_g_s, lambda item: item['win']):
                    d_g_w = list(d_w_group)
                    if d_g_w[0]['win'] == False:
                        break
                    wins = len(d_g_w)
                    dungeons[d_id]['stages'][max_stage - d_s]['wins'] = wins
                    clear_times = [d['clear_time'] for d in d_g_w]
                    avg_time = sum(
                        clear_times, timedelta(0)) / len(clear_times)
                    avg_str = str(avg_time)
                    try:
                        avg_index = avg_str.index('.')
                        avg_str = avg_str[:avg_index]
                    except ValueError:
                        pass
                    dungeons[d_id]['stages'][max_stage -
                                             d_s]['avg_time'] = avg_str

        return Response(list(dungeons.values()))


class DimholeDetailView(APIView):
    permission_classes = [IsSwstatsWeb, ]
    swagger_schema = None

    @cache_response(60 * 15, key_func=calculate_cache_key, cache_errors=False)
    def get(self, request, format=None):
        if 'cid' not in request.GET or 'stage' not in request.GET:
            return Response({}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            cid = request.GET['cid'].split('-')

            if not cid or len(cid) > 2:
                raise ValueError(
                    f"Wrong Dimension Hole ID: {request.GET['cid']}")

            cid = int(cid[0])
            stage = int(request.GET['stage'])

            if cid not in [d[0] for d in DimensionHoleRun.DIM_HOLE_TYPES]:
                raise ValueError(
                    f"Non existing Dimension Hole ID: {request.GET['cid']}")

            task = fetch_dimhole_detail_data.delay(
                list(request.GET.lists()), cid, stage)

            return Response({'status': task.state, 'task_id': task.id})
        except ValueError:
            return Response({}, status=status.HTTP_401_UNAUTHORIZED)


class ReportsOld(APIView):
    permission_classes = [IsSwstatsWeb, ]
    swagger_schema = None

    def get(self, request, format=None):
        images = list()

        app_static_dir = os.path.join(
            settings.BASE_DIR, 'website', 'static', 'website', 'reports')

        for filename in os.listdir(app_static_dir):
            if filename.endswith(".png"):
                images.append({
                    'monster': ' '.join([f.capitalize() for f in filename[:filename.index('_infographic')].split('_')]),
                    'filename': filename,
                    'date': os.path.getmtime(app_static_dir + '/' + filename),
                    'cols': 2 if '&' in filename else 1,
                })

        # reverse=True -> descending
        images = sorted(images, key=lambda image: image['date'], reverse=True)
        for i in range(len(images)):
            images[i]['date'] = datetime.strftime(
                datetime.fromtimestamp(images[i]['date']), "%Y-%m-%d")

        return Response(images)


class ReportsGenerateInit(APIView):
    permission_classes = [IsSwstatsWeb, ]
    swagger_schema = None

    def get(self, request, format=None):
        monsters = list()

        mons = MonsterBase.objects.prefetch_related('monster_set').filter(~Q(archetype=5) & ~Q(awaken=0) & Q(monster__stars=6)).values(
            'id', 'name').annotate(count=Count('monster__id'))  # archetype=5 -> Material Monsters, awaken=0 -> Unawakened, monster__stars=6 -> 6*
        mons = sorted(mons, key=itemgetter('count'), reverse=True)
        monsters = [{
            'id': m['id'],
            'name': f"{m['name']} ({m['count']})",
        } for m in mons]

        return Response(monsters)


class ReportsGenerateMonster(APIView):
    permission_classes = [permissions.AllowAny, ]
    swagger_schema = None

    @cache_response(60 * 15, key_func=calculate_cache_key, cache_errors=False)
    def get(self, request, monster_id=None, format=None):
        if not monster_id:
            return Response({'error', 'No Monster ID given.'}, status=status.HTTP_400_BAD_REQUEST)

        task = generate_monster_report.delay(monster_id)

        return Response({'status': task.state, 'task_id': task.id})


class ReportsBotGenerateMonster(APIView):
    permission_classes = [IsSwstatsWeb, ]
    swagger_schema = None

    @cache_response(60 * 15, key_func=calculate_cache_key, cache_errors=False)
    def get(self, request, monster_id=None, format=None):
        if not monster_id:
            return Response({'error', 'No Monster ID given.'}, status=status.HTTP_400_BAD_REQUEST)

        content = generate_bot_monster_report(monster_id)

        return Response(content)


class MonsterView(APIView):
    permission_classes = [IsSwstatsWeb, ]
    swagger_schema = None

    @cache_response(60 * 15, key_func=calculate_cache_key, cache_errors=False)
    def get(self, request, format=None, mon_id=None):
        start = time.time()
        if not mon_id:
            return Response({'error', 'No Monster ID given.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            mon = Monster.objects.select_related(
                'base_monster',
                'base_monster__family',
            ).prefetch_related(
                'runes',
                'runes__rune_set',
                'runes_rta',
                'runes_rta__rune_set',
                'artifacts',
                'artifacts_rta'
            ).get(id=mon_id)
        except Monster.DoesNotExist:
            return Response({'error': 'Monster doesn`t exist.'}, status=status.HTTP_400_BAD_REQUEST)

        data = MonsterSerializer(mon).data
        print(round(time.time() - start, 4))

        return Response(data)


class StatusView(APIView):
    permission_classes = [permissions.AllowAny, ]
    swagger_schema = None

    def get(self, request, format=None, task_id=None):
        if not task_id:
            return Response({'error': 'Task doesn`t exist'}, status=status.HTTP_400_BAD_REQUEST)
        task = AsyncResult(task_id, app=celery_app)
        if task.state == 'PENDING':
            response = {
                'status': task.state,
                'step': 'Waiting in Queue',
            }
        elif task.state == 'SUCCESS':
            response = {
                'status': task.state,
                'step': task.result,
            }
        elif task.state == 'PROGRESS':
            response = {
                'status': task.state,
                'step': task.info.get('step', ''),
            }
        else:
            response = {
                'status': task.state,
                'step': str(task.info),
            }

        return Response(response)


class ProfileView(APIView):
    permission_classes = [IsSwstatsWeb, ]
    swagger_schema = None

    def post(self, request, format=None):
        if 'command' not in request.data.keys() or request.data['command'] != 'HubUserLogin':
            return Response({'error': "Given File is an invalid Summoners War JSON File."}, status=status.HTTP_400_BAD_REQUEST)

        task = generate_profile_report.delay(request.data)

        return Response({'status': task.state, 'task_id': task.id})
