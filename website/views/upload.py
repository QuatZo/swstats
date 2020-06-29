from django.http import HttpResponse
from rest_framework import viewsets, status

import logging

from website.models import *
from website.serializers import CommandSerializer
from website.exceptions import RecordDoesNotExist
from website.tasks import *

import copy
import math
import datetime
import json
import traceback

logger = logging.getLogger(__name__)

# Create your views here.
class MonsterFamilyUploadViewSet(viewsets.ViewSet):
    def create(self, request):
        if request.data:
            for family in request.data:
                obj, created = MonsterFamily.objects.update_or_create( id=family['id'], defaults=family, )
            return HttpResponse(status=status.HTTP_201_CREATED)
        
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

class MonsterSourceUploadViewSet(viewsets.ViewSet):
    def create(self, request):
        if request.data:
            for source in request.data:
                obj, created = MonsterSource.objects.update_or_create( id=source['id'], defaults=source, )
            return HttpResponse(status=status.HTTP_201_CREATED)
        
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

class MonsterBaseUploadViewSet(viewsets.ViewSet):
     def create(self, request):
        if request.data:
            for base in request.data:
                monster_base = dict()
                ########################################
                # Monster Base Model
                monster_base['id'] = base['id']
                base['id'] = str(base['id'])
                monster_base['family'] = MonsterFamily.objects.get(id=int(base['id'][:-2]))
                monster_base['base_class'] = base['base_class']
                monster_base['name'] = base['name']
                monster_base['attribute'] = int(base['id'][-1])
                monster_base['archetype'] = base['archetype']
                monster_base['awaken'] = base['awaken']
                monster_base['max_skills'] = base['max_skills']
                ########################################

                obj, created = MonsterBase.objects.update_or_create( id=base['id'], defaults=monster_base, )
            return HttpResponse(status=status.HTTP_201_CREATED)
        
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

class MonsterHohUploadViewSet(viewsets.ViewSet):
    def create(self, request):
        if request.data:
            for hoh in request.data:
                monster_hoh = dict()
                ########################################
                # Monster HoH Model
                monster_hoh['monster'] = MonsterBase.objects.get(id=int(hoh['id']))
                monster_hoh['date_open'] = hoh['date_open']
                monster_hoh['date_close'] = hoh['date_close']
                ########################################

                obj, created = MonsterHoh.objects.update_or_create( monster=hoh['id'], defaults=monster_hoh, )
            return HttpResponse(status=status.HTTP_201_CREATED)
        
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

class MonsterFusionUploadViewSet(viewsets.ViewSet):
    def create(self, request):
        if request.data:
            for fusion in request.data:
                monster_fusion = dict()
                ########################################
                # Monster Fusion Model
                monster_fusion['monster'] = MonsterBase.objects.get(id=int(fusion['id']))
                monster_fusion['cost'] = fusion['cost']
                ########################################

                obj, created = MonsterFusion.objects.update_or_create( monster=fusion['id'], defaults=monster_fusion, )
            return HttpResponse(status=status.HTTP_201_CREATED)
        
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

class BuildingUploadViewSet(viewsets.ViewSet):
     def create(self, request):
        if request.data:
            for building in request.data:
                obj, created = Building.objects.update_or_create( id=building['id'], defaults=building, )
            return HttpResponse(status=status.HTTP_201_CREATED)
        
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

class HomunculusUploadViewSet(viewsets.ViewSet):
    def create(self, request):
        if request.data:
            for homie in request.data:
                obj, created = HomunculusSkill.objects.update_or_create( id=homie['id'], defaults=homie, )
            return HttpResponse(status=status.HTTP_201_CREATED)
        
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

class HomunculusBuildUploadViewSet(viewsets.ViewSet):
    def create(self, request):
        if request.data:
            for build in request.data:
                data = dict()
                for key, val in build.items():
                    if key == "homunculus_id":
                        data[key] = MonsterBase.objects.get(id=val)
                        continue
                    data[key] = HomunculusSkill.objects.get(id=val)
                obj, created = HomunculusBuild.objects.update_or_create(depth_1=data['depth_1'], depth_2=data['depth_2'], depth_3=data['depth_3'], depth_4=data['depth_4'], depth_5=data['depth_5'], defaults=data, )
            return HttpResponse(status=status.HTTP_201_CREATED)
        
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

class UploadViewSet(viewsets.ViewSet):
    def create(self, request):
        if request.data:
            if request.data['command'] == 'HubUserLogin':
                handle_profile_upload_task.delay(request.data)

            elif request.data['command'] == 'VisitFriend':
                handle_friend_upload_task.delay(request.data)
            
            elif request.data['command'] == 'GetUnitRecommendPage_V2':
                handle_monster_recommendation_upload_task.delay(request.data['response'], request.data['request'])

            elif request.data['command'] == 'BattleRiftOfWorldsRaidStart': # R5
                handle_raid_start_upload_task.delay(request.data['response'], request.data['request'])
            elif request.data['command'] == 'BattleRiftOfWorldsRaidResult': # R5
                handle_raid_run_upload_task.delay(request.data['response'], request.data['request'])
            
            elif request.data['command'] == 'BattleDungeonResult' or request.data['command'] == 'BattleDungeonResult_V2':
                handle_dungeon_run_upload_task.delay(request.data['response'], request.data['request'])
            
            elif request.data['command'] == 'BattleRiftDungeonStart': # Elemental Rift
                handle_rift_dungeon_start_upload_task.delay(request.data['response'], request.data['request'])
            elif request.data['command'] == 'BattleRiftDungeonResult': # Elemental Rift
                handle_rift_dungeon_run_upload_task.delay(request.data['response'], request.data['request'])
                
            elif request.data['command'] == 'GetGuildSiegeDefenseDeckByWizardId':
                handle_siege_defenses_upload_task.delay(request.data)

            elif request.data['command'] == 'GetGuildSiegeRankingInfo':
                handle_siege_ranking_upload_task.delay(request.data)

            elif request.data['command'] == 'BattleDimensionHoleDungeonResult':
                handle_dimension_hole_run_upload_task.delay(request.data['response'], request.data['request'])

            return HttpResponse(status=status.HTTP_201_CREATED)
            
        logger.error("Given request is invalid")
        return HttpResponse(f"Given request is invalid. Try updating plugin or contact QuatZo on Reddit", status=status.HTTP_400_BAD_REQUEST)

class CommandViewSet(viewsets.ModelViewSet):
    serializer_class = CommandSerializer
    queryset = Command.objects.all()
    http_method_names = ['get']