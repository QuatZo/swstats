from django.http import HttpResponse
from django.core.paginator import Paginator
from django.utils.functional import cached_property

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from rest_framework import viewsets, status, pagination

from website.models import *
from website.serializers import CommandSerializer, MonsterSerializer, RuneSerializer, ArtifactSerializer
from website.tasks import *


class FasterDjangoPaginator(Paginator):
    @cached_property
    def count(self):
        return self.object_list.values('id').count()


class LargeResultsSetPagination(pagination.PageNumberPagination):
    django_paginator_class = FasterDjangoPaginator
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 10000


class RuneViewSet(viewsets.ModelViewSet):
    serializer_class = RuneSerializer
    pagination_class = LargeResultsSetPagination
    http_method_names = ['get']

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('rune_set', openapi.IN_QUERY, "Rune Set", type=openapi.TYPE_STRING, enum=list(
                RuneSet.objects.values_list('name', flat=True))),
            openapi.Parameter('quality', openapi.IN_QUERY, "Rune Quality",
                              type=openapi.TYPE_STRING, enum=Rune().get_rune_qualities()),
            openapi.Parameter('original_quality', openapi.IN_QUERY, "Rune Original Quality",
                              type=openapi.TYPE_STRING, enum=Rune().get_rune_qualities()),
            openapi.Parameter('slot', openapi.IN_QUERY, "Rune Slot",
                              type=openapi.TYPE_INTEGER, enum=[1, 2, 3, 4, 5, 6]),
            openapi.Parameter('stars', openapi.IN_QUERY, "Rune Stars (10+ => Ancient)",
                              type=openapi.TYPE_INTEGER, enum=[1, 2, 3, 4, 5, 6, 11, 12, 13, 14, 15, 16]),
            openapi.Parameter('ancient', openapi.IN_QUERY,
                              "If Rune is Ancient", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('upgrade_min', openapi.IN_QUERY,
                              "Rune Minimum Upgrade Level", type=openapi.TYPE_INTEGER),
            openapi.Parameter('upgrade_max', openapi.IN_QUERY,
                              "Rune Maximum Upgrade Level", type=openapi.TYPE_INTEGER),
            openapi.Parameter('eff_min', openapi.IN_QUERY,
                              "Rune Minimum Efficiency", type=openapi.TYPE_NUMBER),
            openapi.Parameter('eff_max', openapi.IN_QUERY,
                              "Rune Maximum Efficiency", type=openapi.TYPE_NUMBER),
            openapi.Parameter('equipped', openapi.IN_QUERY,
                              "If Rune is Equipped", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('equipped_rta', openapi.IN_QUERY,
                              "If Rune is Equipped in RTA Rune Management", type=openapi.TYPE_BOOLEAN),
        ],
    )
    def list(self, request):
        return super().list(request)

    def get_queryset(self):
        queryset = Rune.objects.all()

        rune_set = self.request.query_params.get('rune_set', None)
        quality = self.request.query_params.get('quality', None)
        original_quality = self.request.query_params.get(
            'original_quality', None)
        slot = self.request.query_params.get('slot', None)
        stars = self.request.query_params.get('stars', None)
        ancient = self.request.query_params.get('ancient', None)
        upgrade_min = self.request.query_params.get('upgrade_min', None)
        upgrade_max = self.request.query_params.get('upgrade_max', None)
        eff_min = self.request.query_params.get('eff_min', None)
        eff_max = self.request.query_params.get('eff_max', None)
        equipped = self.request.query_params.get('equipped', None)
        equipped_rta = self.request.query_params.get('equipped_rta', None)

        if rune_set is not None:
            queryset = queryset.filter(rune_set__name=rune_set)
        if quality is not None:
            queryset = queryset.filter(
                quality=Rune().get_rune_quality_id(quality))
        if original_quality is not None:
            queryset = queryset.filter(
                quality_original=Rune().get_rune_quality_id(original_quality))
        if slot is not None:
            queryset = queryset.filter(slot=slot)
        if stars is not None:
            queryset = queryset.filter(stars=stars)
        if ancient is not None:
            if ancient.lower() == 'true':
                queryset = queryset.filter(stars__gt=6)
            else:
                queryset = queryset.filter(stars__lte=6)
        if upgrade_min is not None:
            queryset = queryset.filter(upgrade_curr__gte=upgrade_min)
        if upgrade_max is not None:
            queryset = queryset.filter(upgrade_curr__lte=upgrade_max)
        if eff_min is not None:
            queryset = queryset.filter(efficiency__gte=eff_min)
        if eff_max is not None:
            queryset = queryset.filter(efficiency__lte=eff_max)
        if equipped is not None:
            if equipped.lower() == 'true':
                queryset = queryset.filter(equipped=True)
            else:
                queryset = queryset.filter(equipped=False)
        if equipped_rta is not None:
            if equipped_rta.lower() == 'true':
                queryset = queryset.filter(equipped_rta=True)
            else:
                queryset = queryset.filter(equipped_rta=False)

        return queryset.prefetch_related('rune_set').order_by('id')


class ArtifactViewSet(viewsets.ModelViewSet):
    serializer_class = ArtifactSerializer
    pagination_class = LargeResultsSetPagination
    http_method_names = ['get']

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('rtype', openapi.IN_QUERY, "Artifact Type",
                              type=openapi.TYPE_STRING, enum=Artifact().get_artifact_types()),
            openapi.Parameter('archetype', openapi.IN_QUERY, "Artifact Archetype",
                              type=openapi.TYPE_STRING, enum=Artifact().get_artifact_archetypes()),
            openapi.Parameter('attribute', openapi.IN_QUERY, "Artifact Attribute",
                              type=openapi.TYPE_STRING, enum=Artifact().get_artifact_attributes()),
            openapi.Parameter('quality', openapi.IN_QUERY, "Artifact Quality",
                              type=openapi.TYPE_STRING, enum=Artifact().get_artifact_qualities()),
            openapi.Parameter('original_quality', openapi.IN_QUERY, "Artifact Original Quality",
                              type=openapi.TYPE_STRING, enum=Artifact().get_artifact_qualities()),
            openapi.Parameter('upgrade_min', openapi.IN_QUERY,
                              "Artifact Minimum Upgrade Level", type=openapi.TYPE_INTEGER),
            openapi.Parameter('upgrade_max', openapi.IN_QUERY,
                              "Artifact Maximum Upgrade Level", type=openapi.TYPE_INTEGER),
            openapi.Parameter('eff_min', openapi.IN_QUERY,
                              "Artifact Minimum Efficiency", type=openapi.TYPE_NUMBER),
            openapi.Parameter('eff_max', openapi.IN_QUERY,
                              "Artifact Maximum Efficiency", type=openapi.TYPE_NUMBER),
            openapi.Parameter('equipped', openapi.IN_QUERY,
                              "If Artifact is Equipped", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('equipped_rta', openapi.IN_QUERY,
                              "If Artifact is Equipped in RTA Rune Management", type=openapi.TYPE_BOOLEAN),
        ],
    )
    def list(self, request):
        return super().list(request)

    def get_queryset(self):
        queryset = Artifact.objects.all().order_by('id')

        rtype = self.request.query_params.get('rtype', None)
        attribute = self.request.query_params.get('attribute', None)
        archetype = self.request.query_params.get('archetype', None)
        quality = self.request.query_params.get('quality', None)
        original_quality = self.request.query_params.get(
            'original_quality', None)
        upgrade_min = self.request.query_params.get('upgrade_min', None)
        upgrade_max = self.request.query_params.get('upgrade_max', None)
        eff_min = self.request.query_params.get('eff_min', None)
        eff_max = self.request.query_params.get('eff_max', None)
        equipped = self.request.query_params.get('equipped', None)
        equipped_rta = self.request.query_params.get('equipped_rta', None)

        if rtype is not None:
            queryset = queryset.filter(
                rtype=Artifact().get_artifact_rtype_id(rtype))
        if attribute is not None:
            queryset = queryset.filter(
                attribute=Artifact().get_artifact_attribute_id(attribute))
        if archetype is not None:
            queryset = queryset.filter(
                archetype=Artifact().get_artifact_archetype_id(archetype))
        if quality is not None:
            queryset = queryset.filter(
                quality=Artifact().get_artifact_quality_id(quality))
        if original_quality is not None:
            queryset = queryset.filter(
                quality_original=Artifact().get_artifact_quality_id(original_quality))
        if upgrade_min is not None:
            queryset = queryset.filter(level__gte=upgrade_min)
        if upgrade_max is not None:
            queryset = queryset.filter(level__lte=upgrade_max)
        if eff_min is not None:
            queryset = queryset.filter(efficiency__gte=eff_min)
        if eff_max is not None:
            queryset = queryset.filter(efficiency__lte=eff_max)
        if equipped is not None:
            if equipped.lower() == 'true':
                queryset = queryset.filter(equipped=True)
            else:
                queryset = queryset.filter(equipped=False)
        if equipped_rta is not None:
            if equipped_rta.lower() == 'true':
                queryset = queryset.filter(equipped_rta=True)
            else:
                queryset = queryset.filter(equipped_rta=False)

        return queryset


class MonsterViewSet(viewsets.ModelViewSet):
    serializer_class = MonsterSerializer
    pagination_class = LargeResultsSetPagination
    http_method_names = ['get']

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('base_class', openapi.IN_QUERY, "Monster Natural Stars",
                              type=openapi.TYPE_STRING, enum=[1, 2, 3, 4, 5, 6]),
            openapi.Parameter('family', openapi.IN_QUERY, "Monster Family", type=openapi.TYPE_STRING, enum=list(
                MonsterFamily.objects.values_list('name', flat=True))),
            openapi.Parameter('attribute', openapi.IN_QUERY, "Monster Attribute",
                              type=openapi.TYPE_STRING, enum=MonsterBase().get_monster_attributes()),
            openapi.Parameter('archetype', openapi.IN_QUERY, "Monster Archetype",
                              type=openapi.TYPE_STRING, enum=MonsterBase().get_monster_archetypes()),
            openapi.Parameter('base_monster', openapi.IN_QUERY, "Base Monster", type=openapi.TYPE_STRING, enum=list(
                MonsterBase.objects.values_list('name', flat=True))),
            openapi.Parameter('awaken', openapi.IN_QUERY, "Monster Awaken Status",
                              type=openapi.TYPE_STRING, enum=list(MonsterBase().get_awaken_as_dict().values())),
            openapi.Parameter('level_min', openapi.IN_QUERY,
                              "Monster Minimum Level", type=openapi.TYPE_INTEGER),
            openapi.Parameter('stars', openapi.IN_QUERY, "Monster Stars",
                              type=openapi.TYPE_INTEGER, enum=[1, 2, 3, 4, 5, 6]),

            openapi.Parameter('hp', openapi.IN_QUERY, "Monster HP (min,max)", type=openapi.TYPE_ARRAY,
                              items=openapi.Items(type=openapi.TYPE_INTEGER), min_items=2, max_items=2),
            openapi.Parameter('attack', openapi.IN_QUERY, "Monster Attack (min,max)", type=openapi.TYPE_ARRAY,
                              items=openapi.Items(type=openapi.TYPE_INTEGER), min_items=2, max_items=2),
            openapi.Parameter('defense', openapi.IN_QUERY, "Monster Defense (min,max)", type=openapi.TYPE_ARRAY,
                              items=openapi.Items(type=openapi.TYPE_INTEGER), min_items=2, max_items=2),
            openapi.Parameter('speed', openapi.IN_QUERY, "Monster Speed (min,max)", type=openapi.TYPE_ARRAY,
                              items=openapi.Items(type=openapi.TYPE_INTEGER), min_items=2, max_items=2),
            openapi.Parameter('res', openapi.IN_QUERY, "Monster Resistance (min,max)", type=openapi.TYPE_ARRAY,
                              items=openapi.Items(type=openapi.TYPE_INTEGER), min_items=2, max_items=2),
            openapi.Parameter('acc', openapi.IN_QUERY, "Monster Accuracy (min,max)", type=openapi.TYPE_ARRAY,
                              items=openapi.Items(type=openapi.TYPE_INTEGER), min_items=2, max_items=2),
            openapi.Parameter('crit_rate', openapi.IN_QUERY, "Monster Critical rate (min,max)",
                              type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_INTEGER), min_items=2, max_items=2),
            openapi.Parameter('crit_dmg', openapi.IN_QUERY, "Monster Critical Damage (min,max)",
                              type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_INTEGER), min_items=2, max_items=2),
            openapi.Parameter('eff_hp', openapi.IN_QUERY, "Monster Effective HP (min,max)", type=openapi.TYPE_ARRAY,
                              items=openapi.Items(type=openapi.TYPE_INTEGER), min_items=2, max_items=2),
            openapi.Parameter('eff_hp_def_break', openapi.IN_QUERY, "Monster Effective HP with Def Break (min,max)",
                              type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_INTEGER), min_items=2, max_items=2),
            openapi.Parameter('avg_eff', openapi.IN_QUERY, "Monster Average Efficiency (min,max)",
                              type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_NUMBER), min_items=2, max_items=2),

            openapi.Parameter('transmog', openapi.IN_QUERY,
                              "If Monster has Transmog", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('storage', openapi.IN_QUERY,
                              "If Monster is in Storage", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('locked', openapi.IN_QUERY,
                              "If Monster is Locked", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('runes', openapi.IN_QUERY,
                              "If Monster has 6 equipped Runes", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('runes_rta', openapi.IN_QUERY,
                              "If Monster has 6 equipped Runes in RTA Rune Management System", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('artifacts', openapi.IN_QUERY,
                              "If Monster has 2 equipped Artifacts", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('artifacts_rta', openapi.IN_QUERY,
                              "If Monster has 2 equipped Artifacts in RTA Rune Management System", type=openapi.TYPE_BOOLEAN),
        ],
    )
    def list(self, request):
        return super().list(request)

    def get_queryset(self):
        queryset = Monster.objects.all()

        base_class = self.request.query_params.get('base_class', None)
        family = self.request.query_params.get('family', None)
        attribute = self.request.query_params.get('attribute', None)
        archetype = self.request.query_params.get('archetype', None)
        base_monster = self.request.query_params.get('base_monster', None)
        awaken = self.request.query_params.get('awaken', None)
        level_min = self.request.query_params.get('level_min', None)
        stars = self.request.query_params.get('stars', None)
        hp = self.request.query_params.get('hp', None)
        attack = self.request.query_params.get('attack', None)
        defense = self.request.query_params.get('defense', None)
        speed = self.request.query_params.get('speed', None)
        res = self.request.query_params.get('res', None)
        acc = self.request.query_params.get('acc', None)
        crit_rate = self.request.query_params.get('crit_rate', None)
        crit_dmg = self.request.query_params.get('crit_dmg', None)
        eff_hp = self.request.query_params.get('eff_hp', None)
        eff_hp_def_break = self.request.query_params.get(
            'eff_hp_def_break', None)
        avg_eff = self.request.query_params.get('avg_eff', None)
        transmog = self.request.query_params.get('transmog', None)
        storage = self.request.query_params.get('storage', None)
        locked = self.request.query_params.get('locked', None)
        runes = self.request.query_params.get('runes', None)
        runes_rta = self.request.query_params.get('runes_rta', None)
        artifacts = self.request.query_params.get('artifacts', None)
        artifacts_rta = self.request.query_params.get('artifacts_rta', None)

        if base_class is not None:
            queryset = queryset.filter(base_monster__base_class=base_class)
        if family is not None:
            queryset = queryset.filter(base_monster__family__name=family)
        if attribute is not None:
            queryset = queryset.filter(
                base_monster__attribute=MonsterBase().get_attribute_id(attribute))
        if archetype is not None:
            queryset = queryset.filter(
                base_monster__archetype=MonsterBase().get_archetype_id(archetype))
        if base_monster is not None:
            queryset = queryset.filter(base_monster__name=base_monster)
        if awaken is not None:
            queryset = queryset.filter(
                base_monster__awaken=MonsterBase().get_awaken_id(awaken))
        if level_min is not None:
            queryset = queryset.filter(level__gte=level_min)
        if stars is not None:
            queryset = queryset.filter(stars=stars)
        if hp is not None and ',' in hp:
            if len(hp.split(',')) == 2:
                hp_min, hp_max = hp.split(',')
                queryset = queryset.filter(hp__gte=hp_min, hp__lte=hp_max)
        if attack is not None and ',' in attack:
            if len(attack.split(',')) == 2:
                attack_min, attack_max = attack.split(',')
                queryset = queryset.filter(
                    attack__gte=attack_min, attack__lte=attack_max)
        if defense is not None and ',' in defense:
            if len(defense.split(',')) == 2:
                defense_min, defense_max = defense.split(',')
                queryset = queryset.filter(
                    defense__gte=defense_min, defense__lte=defense_max)
        if speed is not None and ',' in speed:
            if len(speed.split(',')) == 2:
                speed_min, speed_max = speed.split(',')
                queryset = queryset.filter(
                    speed__gte=speed_min, speed__lte=speed_max)
        if res is not None and ',' in res:
            if len(res.split(',')) == 2:
                res_min, res_max = res.split(',')
                queryset = queryset.filter(res__gte=res_min, res__lte=res_max)
        if acc is not None and ',' in acc:
            if len(acc.split(',')) == 2:
                acc_min, acc_max = acc.split(',')
                queryset = queryset.filter(acc__gte=acc_min, acc__lte=acc_max)
        if crit_rate is not None and ',' in crit_rate:
            if len(crit_rate.split(',')) == 2:
                crit_rate_min, crit_rate_max = crit_rate.split(',')
                queryset = queryset.filter(
                    crit_rate__gte=crit_rate_min, crit_rate__lte=crit_rate_max)
        if crit_dmg is not None and ',' in crit_dmg:
            if len(crit_dmg.split(',')) == 2:
                crit_dmg_min, crit_dmg_max = crit_dmg.split(',')
                queryset = queryset.filter(
                    crit_dmg__gte=crit_dmg_min, crit_dmg__lte=crit_dmg_max)
        if eff_hp is not None and ',' in eff_hp:
            if len(eff_hp.split(',')) == 2:
                eff_hp_min, eff_hp_max = eff_hp.split(',')
                queryset = queryset.filter(
                    eff_hp__gte=eff_hp_min, eff_hp__lte=eff_hp_max)
        if eff_hp_def_break is not None and ',' in eff_hp_def_break:
            if len(eff_hp_def_break.split(',')) == 2:
                eff_hp_def_break_min, eff_hp_def_break_max = eff_hp_def_break.split(
                    ',')
                queryset = queryset.filter(
                    eff_hp_def_break__gte=eff_hp_def_break_min, eff_hp_def_break__lte=eff_hp_def_break_max)
        if avg_eff is not None and ',' in avg_eff:
            if len(avg_eff.split(',')) == 2:
                avg_eff_total_min, avg_eff_total_max = avg_eff.split(',')
                queryset = queryset.filter(
                    avg_eff_total__gte=avg_eff_total_min, avg_eff_total__lte=avg_eff_total_max)
        if transmog is not None:
            if transmog.lower() == 'true':
                queryset = queryset.filter(transmog=True)
            else:
                queryset = queryset.filter(transmog=False)
        if storage is not None:
            if storage.lower() == 'true':
                queryset = queryset.filter(storage=True)
            else:
                queryset = queryset.filter(storage=False)
        if locked is not None:
            if locked.lower() == 'true':
                queryset = queryset.filter(locked=True)
            else:
                queryset = queryset.filter(locked=False)
        if runes is not None:
            if runes.lower() == 'true':
                queryset = queryset.annotate(
                    runes_count=Count('runes')).filter(runes_count=6)
            else:
                queryset = queryset.annotate(
                    runes_count=Count('runes')).filter(runes_count__lt=6)
        if runes_rta is not None:
            if runes_rta.lower() == 'true':
                queryset = queryset.annotate(runes_rta_count=Count(
                    'runes_rta')).filter(runes_rta_count=6)
            else:
                queryset = queryset.annotate(runes_rta_count=Count(
                    'runes_rta')).filter(runes_rta_count__lt=6)
        if artifacts is not None:
            if artifacts.lower() == 'true':
                queryset = queryset.annotate(artifacts_count=Count(
                    'artifacts')).filter(artifacts_count=2)
            else:
                queryset = queryset.annotate(artifacts_count=Count(
                    'artifacts')).filter(artifacts_count__lt=2)
        if artifacts_rta is not None:
            if artifacts_rta.lower() == 'true':
                queryset = queryset.annotate(artifacts_rta_count=Count(
                    'artifacts_rta')).filter(artifacts_rta_count=2)
            else:
                queryset = queryset.annotate(artifacts_rta_count=Count(
                    'artifacts_rta')).filter(artifacts_rta_count__lt=2)

        return queryset.prefetch_related('base_monster', 'base_monster__family', 'runes', 'runes_rta', 'runes__rune_set', 'runes_rta__rune_set', 'artifacts', 'artifacts_rta', ).order_by('id')
