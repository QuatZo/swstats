import pandas as pd
import numpy as np
import datetime
import math
import time
import itertools
from operator import itemgetter
from datetime import timedelta
import statistics

from django.db.models import F, Q, Avg, Min, Max, Sum, Count, FloatField, Func

from website.models import *
from website.functions import calc_efficiency
from .serializers import RuneFullSerializer, MonsterSerializer, ArtifactSerializer, SiegeSerializer, MonsterBaseSerializer


def get_scoring_system():
    points = {
        "wizard": {
            "active_contributor": 1000,
            "mana_100k": 1,
            "crystals_10": 1,
            "level": 5,
            "antibot_count": 1,
            "raid": 20,
            "storage_capacity": .25,
        },
        "guild": {
            "gw_rank":  50,
            "siege_rank":  50,
        },
        "buildings": {
            "max":  20,
            "max_all":  250,
        },
        "flags": {
            "max":  50,
            "max_all":  200,
        },
        "runes": {
            "count": .1,
            "stars_5_legend": 2,
            "stars_6_hero": 2,
            "stars_6_legend": 5,
            "upgrade_12": .1,
            "upgrade_15": .5,
            "sub_speed": {
                'total': [5, 15, 50],
                'threshold': [20, 28, 33],
            },
            "sub_hp": {
                'total': [5, 15, 50],
                'threshold': [27, 35, 45],
            },
            "sub_def": {
                'total': [5, 15, 50],
                'threshold': [27, 35, 45],
            },
            "sub_atk": {
                'total': [5, 15, 50],
                'threshold': [27, 35, 45],
            },
            "sub_crit_rate": {
                'total': [5, 15, 50],
                'threshold': [20, 28, 33],
            },
            "sub_crit_dmg": {
                'total': [5, 15, 50],
                'threshold': [23, 27, 33],
            },
        },
        "monsters": {
            "count": .1,
            "nat4": 2,
            "nat5": 5,
            "stars_6": 5,
            "transmog": 1,
            "with_runes": 1,
            "skillup": .1,
            "skillups_max": 5,
            "speed": {
                'total': [5, 15, 50],
                'threshold': [200, 250, 300],
            },
            "hp": {
                'total': [5, 15, 50],
                'threshold': [30000, 37500, 45000],
            },
            "defense": {
                'total': [5, 15, 50],
                'threshold': [1750, 2250, 2500],
            },
            "attack": {
                'total': [5, 15, 50],
                'threshold': [2000, 2500, 3000],
            },
            "crit_dmg": {
                'total': [5, 15, 50],
                'threshold': [150, 200, 250],
            },
            "crit_rate": {
                'total': [5, 15, 50],
                'threshold': [80, 90, 100],
            },
            "acc": {
                'total': [5, 15, 50],
                'threshold': [55, 70, 85],
            },
            "res": {
                'total': [5, 15, 50],
                'threshold': [70, 85, 100],
            },
        },
        "total": {
            "wizard": 0,
            "guild": 0,
            "buildings": 0,
            "flags": 0,
            "runes": 0,
            "monsters": 0,
        },
        "sum": 0,
    }

    return points


def _calc_total_per_category(points):
    total = points['total']
    for key, val in points.items():
        if key == 'total' or key == 'sum':
            continue
        for _, vval in val.items():
            if isinstance(vval, float) or isinstance(vval, int):
                total[key] += vval
            else:
                total[key] += sum(vval['total'])

    points['total'] = {k: round(v, 2) for k, v in total.items()}
    points['sum'] = round(sum(total.values()), 2)

    return points


def _round_everything(points):
    for key in points.keys():
        if isinstance(points[key], int) or isinstance(points[key], float):
            points[key] = round(points[key], 2)
        elif isinstance(points[key], list) or isinstance(points[key], tuple):
            points[key] = [round(v, 2) for v in points[key]]
        elif isinstance(points[key], dict):
            points[key] = _round_everything(points[key])

    return points


def get_scoring_for_profile(wizard_id):
    start = time.time()
    points = get_scoring_system()
    wiz = Wizard.objects.get(id=wizard_id)
    runes = Rune.objects.filter(wizard=wiz).select_related('rune_set')
    monsters = Monster.objects.filter(wizard=wiz).select_related(
        'base_monster',
        'base_monster__family', ).prefetch_related(
        'runes',
        'runes__rune_set',
        'artifacts'
    ).defer('runes_rta', 'artifacts_rta', ).order_by()
    buildings = WizardBuilding.objects.filter(
        wizard=wiz).prefetch_related('building')

    last_week = datetime.datetime.now() - datetime.timedelta(days=7)
    # active contributor
    active_contributor = sum([
        DungeonRun.objects.filter(wizard=wiz, date__gte=last_week).count(),
        DimensionHoleRun.objects.filter(
            wizard=wiz, date__gte=last_week).count(),
        RaidDungeonRun.objects.filter(wizard=wiz, date__gte=last_week).count(),
        RiftDungeonRun.objects.filter(wizard=wiz, date__gte=last_week).count(),
    ])

    if active_contributor < 50:
        points['wizard']['active_contributor'] = 0
    ####

    # guild
    points['guild']['gw_rank'] = math.floor(
        wiz.guild.gw_best_ranking / 1000) * points['guild']['gw_rank'] if wiz.guild.gw_best_ranking else 0
    points['guild']['siege_rank'] = math.floor(
        wiz.guild.siege_ranking / 1000) * points['guild']['siege_rank'] if wiz.guild.siege_ranking else 0
    ####

    # wizard
    points['wizard']['mana_100k'] *= math.floor(wiz.mana / 100000)
    points['wizard']['crystals_10'] *= math.floor(wiz.crystals / 10)
    points['wizard']['level'] *= wiz.level

    points['wizard']['antibot_count'] *= wiz.antibot_count
    points['wizard']['raid'] *= wiz.raid_level
    points['wizard']['storage_capacity'] *= wiz.storage_capacity
    ####

    # buildings
    a_b = buildings.filter(building__area=Building().get_area_id('Arena'))
    a_b_max_count = a_b.filter(level=20).count()
    points['buildings']['max'] *= a_b_max_count
    if a_b_max_count != a_b.count():
        points['buildings']['max_all'] = 0
    ####

    # flags
    g_b = buildings.filter(building__area=Building().get_area_id('Guild'))
    g_b_max_count = g_b.filter(level=10).count()
    points['flags']['max'] *= g_b_max_count
    if g_b_max_count != g_b.count():
        points['flags']['max_all'] = 0
    ####

    # runes
    points['runes']['count'] *= runes.count()
    points['runes']['stars_5_legend'] *= runes.filter(
        stars__gte=5, quality_original__in=[5, 15]).count()
    points['runes']['stars_6_hero'] *= runes.filter(
        stars=6, quality_original__in=[4, 14, 5, 15]).count()
    points['runes']['stars_6_legend'] *= runes.filter(
        stars=6, quality_original__in=[5, 15]).count()
    points['runes']['upgrade_12'] *= runes.filter(
        upgrade_curr__gte=12).count()
    points['runes']['upgrade_15'] *= runes.filter(
        upgrade_curr=15).count()

    runes_substats = ['sub_speed', 'sub_hp', 'sub_atk',
                      'sub_def', 'sub_crit_rate', 'sub_crit_dmg']
    df_runes = pd.DataFrame(
        list(runes.values(*runes_substats))).applymap(lambda x: sum(x) if x else None)
    for r_s in runes_substats:
        points['runes'][r_s]['total'] = [df_runes[df_runes[r_s] > points['runes'][r_s]['threshold'][j]].shape[0]
                                         * points['runes'][r_s]['total'][j] for j in range(len(points['runes'][r_s]['threshold']))]
    ####

    # monsters
    points['monsters']['count'] *= monsters.count()
    points['monsters']['nat4'] *= monsters.filter(
        base_monster__base_class=4).count()
    points['monsters']['nat5'] *= monsters.filter(
        base_monster__base_class=5).count()
    points['monsters']['stars_6'] *= monsters.filter(stars=6).count()
    points['monsters']['transmog'] *= monsters.filter(
        transmog=True).count()

    monsters = monsters.exclude(base_monster__archetype=5).exclude(
        base_monster__archetype=0)  # material monsters
    monsters = pd.DataFrame(list(monsters.values(*['id', 'runes', 'skills', 'base_monster__max_skills', 'speed', 'hp', 'attack',
                                                   'defense', 'crit_rate', 'crit_dmg', 'res', 'acc']))).applymap(lambda x: sum(x) if isinstance(x, list) else x).drop_duplicates('id')

    points['monsters']['with_runes'] *= monsters[monsters['runes'] == 6].shape[0]
    points['monsters']['skillups_max'] *= monsters[monsters['skills']
                                                   == monsters['base_monster__max_skills']].shape[0]
    points['monsters']['skillup'] *= monsters['skills'].sum()
    points['monsters']['skillup'] = round(points['monsters']['skillup'], 2)

    for m_s in ['speed', 'hp', 'attack', 'defense', 'crit_rate', 'crit_dmg', 'res', 'acc']:
        points['monsters'][m_s]['total'] = [monsters[monsters[m_s] > points['monsters'][m_s]['threshold'][j]].shape[0]
                                            * points['monsters'][m_s]['total'][j] for j in range(len(points['monsters'][m_s]['threshold']))]
    ####

    points = _calc_total_per_category(points)
    points = _round_everything(points)

    return points


def calc_monster_comparison_stats(id_, hp, attack, defense, speed, res, acc, crit_rate, crit_dmg, avg_eff_total, eff_hp, base_name, base_id, base_family, base_awaken, df_group, df_group_len, df_means):
    filename = 'monster_'

    if base_id % 100 > 10:
        if base_id % 100 > 20:
            filename += 'second'
        filename += 'awakened_' + base_name.lower().replace('(2a)', '').replace(' ', '')
        if 'homunculus' in filename:
            filename = filename.replace(
                '-', '_').replace('(', '_').replace(')', '')
    else:
        filename += base_name.lower().replace(' (', '_').replace(')', '').replace(' ', '')

    img_url = 'https://swstats.info/static/website/images/monsters/' + filename + '.png'

    kw = {
        'hp': hp,
        'attack': attack,
        'defense': defense,
        'speed': speed,
        'res': res,
        'acc': acc,
        'crit_rate': crit_rate,
        'crit_dmg': crit_dmg,
        'avg_eff_total': avg_eff_total,
        'eff_hp': eff_hp,
    }
    m_stats = {
        'id': id_,
        'img_url': img_url,
        'name': f'{base_name} ({base_family})' if base_awaken > 0 else base_name,
        'rank': dict()
    }
    for key, val in kw.items():
        m_stats['rank'][key] = {
            'top': round(len(df_group[df_group[key] > val]) / df_group_len * 100, 2),
            'avg': val - df_means[key],
            'val': val,
        }
        if m_stats['rank'][key]['top'] == 0:
            m_stats['rank'][key]['top'] = "Best"

        if key == 'avg_eff_total':
            m_stats['rank'][key]['avg'] = round(m_stats['rank'][key]['avg'], 2)
        else:
            m_stats['rank'][key]['avg'] = int(
                round(m_stats['rank'][key]['avg']))

    return m_stats


def calc_rune_comparison_stats(id_, hp_f, hp, atk_f, atk, def_f, def_, spd, res, acc, c_rate, c_dmg, eff, primary, slot, quality, quality_original, rune_set, df_group, df_group_len, df_means):
    img_url = {
        'id': id_,
        'slot': slot,
        'quality': Rune.get_rune_quality(quality),
        'quality_original': Rune.get_rune_quality(quality_original),
        'image': f'https://swstats.info/static/website/images/runes/{rune_set.lower()}.png',
    }

    kw = {
        'sub_hp_flat': hp_f,
        'sub_hp': hp,
        'sub_atk_flat': atk_f,
        'sub_atk': atk,
        'sub_def_flat': def_f,
        'sub_def': def_,
        'sub_speed': spd,
        'sub_res': res,
        'sub_acc': acc,
        'sub_crit_rate': c_rate,
        'sub_crit_dmg': c_dmg,
        'efficiency': eff
    }
    r_stats = {
        'id': id_,
        'img_url': img_url,
        'rune_set': rune_set,
        'mainstat': Rune.get_rune_primary(primary),
        'rank': dict()
    }
    for key, val in kw.items():
        r_stats['rank'][key] = {
            'top': round(len(df_group[df_group[key] > val]) / df_group_len * 100, 2) if val else None,
            'avg': val - df_means[key] if val else None,
            'val': val if val else None,
        }
        if r_stats['rank'][key]['top'] == 0:
            r_stats['rank'][key]['top'] = "Best"
        if key == 'efficiency':
            r_stats['rank'][key]['avg'] = round(r_stats['rank'][key]['avg'], 2)
        elif r_stats['rank'][key]['avg']:
            r_stats['rank'][key]['avg'] = int(
                round(r_stats['rank'][key]['avg']))

    return r_stats


def get_profile_comparison_with_database(wizard_id):
    monsters = Monster.objects.select_related('base_monster', 'base_monster__family', ).exclude(base_monster__archetype=5).exclude(base_monster__archetype=0).filter(
        stars=6).defer('runes', 'runes_rta', 'artifacts', 'artifacts_rta').order_by('base_monster__name')  # w/o material, unknown; only 6*
    monsters_cols = ['id', 'wizard__id', 'base_monster__name', 'base_monster__id', 'base_monster__family__name', 'base_monster__awaken', 'hp', 'attack', 'defense', 'speed',
                     'res', 'acc', 'crit_rate', 'crit_dmg', 'avg_eff_total', 'eff_hp']
    df_monsters = pd.DataFrame(monsters.values_list(
        *monsters_cols), columns=monsters_cols).drop_duplicates(subset=['id'])

    runes = Rune.objects.select_related('rune_set', ).filter(upgrade_curr__gte=12).order_by(
        'slot', 'rune_set', '-quality_original')  # only +12-+15
    runes_kw = {
        'sub_hp_flat_sum': Func(F('sub_hp_flat'), function='unnest'),
        'sub_hp_sum': Func(F('sub_hp'), function='unnest'),
        'sub_atk_flat_sum': Func(F('sub_atk_flat'), function='unnest'),
        'sub_atk_sum': Func(F('sub_atk'), function='unnest'),
        'sub_def_flat_sum': Func(F('sub_def_flat'), function='unnest'),
        'sub_def_sum': Func(F('sub_def'), function='unnest'),
        'sub_speed_sum': Func(F('sub_speed'), function='unnest'),
        'sub_res_sum': Func(F('sub_res'), function='unnest'),
        'sub_acc_sum': Func(F('sub_acc'), function='unnest'),
        'sub_crit_rate_sum': Func(F('sub_crit_rate'), function='unnest'),
        'sub_crit_dmg_sum': Func(F('sub_crit_dmg'), function='unnest'),
    }
    runes = runes.annotate(**runes_kw)
    runes_cols = ['id', 'wizard__id', 'slot', 'rune_set__id', 'rune_set__name', 'primary', 'efficiency', 'quality', 'quality_original',
                  'sub_hp_sum', 'sub_hp_flat_sum', 'sub_atk_sum', 'sub_atk_flat_sum', 'sub_def_sum', 'sub_def_flat_sum', 'sub_speed_sum',
                  'sub_res_sum', 'sub_acc_sum', 'sub_crit_rate_sum', 'sub_crit_dmg_sum']
    df_runes = pd.DataFrame(runes.values_list(*runes_cols), columns=[runes_col.replace(
        '_sum', '') for runes_col in runes_cols]).drop_duplicates(subset=['id']).fillna(0)

    comparison = {
        "monsters": [],
        "runes": [],
    }

    df_groups = df_monsters.groupby('base_monster__name', axis=0)
    for _, df_group in df_groups:
        df_wiz = df_group[df_group['wizard__id'] == wizard_id]
        df_means = df_group.mean()
        comparison['monsters'] += [calc_monster_comparison_stats(*row, df_group, len(df_group), df_means) for row in zip(
            df_wiz['id'],
            df_wiz['hp'],
            df_wiz['attack'],
            df_wiz['defense'],
            df_wiz['speed'],
            df_wiz['res'],
            df_wiz['acc'],
            df_wiz['crit_rate'],
            df_wiz['crit_dmg'],
            df_wiz['avg_eff_total'],
            df_wiz['eff_hp'],
            df_wiz['base_monster__name'],
            df_wiz['base_monster__id'],
            df_wiz['base_monster__family__name'],
            df_wiz['base_monster__awaken'],
        )]

    df_groups = df_runes.groupby(['slot', 'rune_set__id', 'primary'])
    for _, df_group in df_groups:
        df_wiz = df_group[df_group['wizard__id'] == wizard_id]
        df_means = df_group.mean()
        comparison['runes'] += [calc_rune_comparison_stats(*row, df_group, len(df_group), df_means) for row in zip(
            df_wiz['id'],
            df_wiz['sub_hp_flat'],
            df_wiz['sub_hp'],
            df_wiz['sub_atk_flat'],
            df_wiz['sub_atk'],
            df_wiz['sub_def_flat'],
            df_wiz['sub_def'],
            df_wiz['sub_speed'],
            df_wiz['sub_res'],
            df_wiz['sub_acc'],
            df_wiz['sub_crit_rate'],
            df_wiz['sub_crit_dmg'],
            df_wiz['efficiency'],
            df_wiz['primary'],
            df_wiz['slot'],
            df_wiz['quality'],
            df_wiz['quality_original'],
            df_wiz['rune_set__name']
        )]

    return comparison


def filter_runes(filters):
    proper_filters = {}
    for key, val in filters:
        if key in ['innate', 'primary', 'quality', 'quality_original', 'rune_set_id', 'slot', 'stars']:
            proper_filters[key + '__in'] = val
        elif key in ['efficiency', 'upgrade_curr']:
            proper_val = [float(v) for v in val]
            proper_val.sort()
            proper_filters[key + '__gte'] = proper_val[0]
            proper_filters[key + '__lte'] = proper_val[1]
        elif key in ['equipped', 'equipped_rta', 'locked']:
            proper_filters[key] = val[0] == 'true'
        elif key == 'substats':
            for substat in val:
                proper_filters[substat + '__isnull'] = False
    return proper_filters


def get_runes_table(request, filters=None):
    runes = Rune.objects.all().select_related('rune_set', ).defer(
        'wizard', 'base_value', 'sell_value').order_by()

    if request:  # ajax call on page change
        filters = list(request.GET.lists())

        proper_filters = filter_runes(filters)
        runes = runes.filter(**proper_filters)

        sort_order = request.GET['sort_order'] if 'sort_order' in request.GET else None
        if sort_order:
            if '-' in sort_order:
                runes = runes.order_by(F(sort_order[1:]).desc(nulls_last=True))
            else:
                runes = runes.order_by(F(sort_order).asc(nulls_first=True))

        page = int(request.GET['page']) if 'page' in request.GET else 1
        count = runes.count()
        PER_PAGE = 10
        start = PER_PAGE * (page - 1)
        end = start + 10
        serializer = RuneFullSerializer(
            runes[start:min(end, count)], many=True)

        return {
            'count': count,
            'page': page,
            'data': serializer.data,
        }

    # filters here
    if filters:
        proper_filters = filter_runes(filters)
        runes = runes.filter(**proper_filters)

    serializer = RuneFullSerializer(runes[:10], many=True)

    return {
        'count': runes.count(),
        'page': 1,
        'data': serializer.data,
    }


def filter_monsters(filters):
    proper_filters = {}
    for key, val in filters:
        # multi select
        if key in ['stars', 'base_monster__base_class', 'base_monster__attribute', 'base_monster__archetype', 'base_monster__awaken', 'base_monster__family']:
            proper_filters[key + '__in'] = val
        # slider
        elif key in [
            'hp',
            'attack',
            'defense',
            'speed',
            'res',
            'acc',
            'crit_rate',
            'crit_dmg',
            'eff_hp',
            'avg_eff_total',
        ]:
            proper_val = [float(v) for v in val]
            proper_val.sort()
            proper_filters[key + '__gte'] = proper_val[0]
            proper_filters[key + '__lte'] = proper_val[1]
        # select
        elif key in ['locked']:
            proper_filters[key] = val[0] == 'true'

    return proper_filters


def get_monsters_table(request, filters=None):
    monsters = Monster.objects.exclude(base_monster__archetype__in=[0, 5]).select_related('base_monster', 'base_monster__family', ).prefetch_related(
        'runes', 'runes_rta', 'artifacts', 'artifacts_rta', 'runes__rune_set', 'runes_rta__rune_set', ).defer('wizard', 'source', 'transmog', ).order_by()

    if request:  # ajax call on page change
        filters = list(request.GET.lists())

        # filters here
        proper_filters = filter_monsters(filters)
        # text for multi field, can't be in dict like others
        try:
            filter_keys = [f[0] for f in filters]
            b_m = filter_keys.index('base_monster__name')
            name_filter = (
                Q(base_monster__name__icontains=filters[b_m][1][0])
                | Q(base_monster__family__name__icontains=filters[b_m][1][0])
            )
            monsters = monsters.filter(name_filter, **proper_filters)
        except ValueError:
            monsters = monsters.filter(**proper_filters)

        sort_order = request.GET['sort_order'].replace(
            '.', '__') if 'sort_order' in request.GET else None
        if sort_order:
            if '-' in sort_order:
                monsters = monsters.order_by(
                    F(sort_order[1:]).desc(nulls_last=True))
            else:
                monsters = monsters.order_by(
                    F(sort_order).asc(nulls_first=True))

        page = int(request.GET['page']) if 'page' in request.GET else 1
        count = monsters.count()
        PER_PAGE = 10
        start = PER_PAGE * (page - 1)
        end = start + 10
        serializer = MonsterSerializer(
            monsters[start:min(end, count)], many=True)

        return {
            'count': count,
            'page': page,
            'data': serializer.data,
        }

    # filters here
    proper_filters = filter_monsters(filters)
    # text for multi field, can't be in dict like others
    try:
        filter_keys = [f[0] for f in filters]
        b_m = filter_keys.index('base_monster__name')
        name_filter = (
            Q(base_monster__name__icontains=filters[b_m][1][0])
            | Q(base_monster__family__name__icontains=filters[b_m][1][0])
        )
        monsters = monsters.filter(name_filter, **proper_filters)
    except ValueError:
        monsters = monsters.filter(**proper_filters)

    serializer = MonsterSerializer(monsters[:10], many=True)

    return {
        'count': monsters.count(),
        'page': 1,
        'data': serializer.data,
    }


def filter_artifacts(filters):
    proper_filters = {}
    for key, val in filters:
        if key in ['rtype', 'quality', 'quality_original', 'primary']:
            proper_filters[key + '__in'] = val
        elif key in ['efficiency', 'level']:
            proper_val = [float(v) for v in val]
            proper_val.sort()
            proper_filters[key + '__gte'] = proper_val[0]
            proper_filters[key + '__lte'] = proper_val[1]
        elif key in ['equipped', 'equipped_rta', 'locked']:
            proper_filters[key] = val[0] == 'true'
        elif key in ['substats']:
            proper_filters[key + '__contains'] = val
    return proper_filters


def get_artifacts_table(request, filters=None):
    artifacts = Artifact.objects.all().defer('wizard').order_by()

    if request:  # ajax call on page change
        filters = list(request.GET.lists())

        proper_filters = filter_artifacts(filters)
        artifacts = artifacts.filter(**proper_filters)

        sort_order = request.GET['sort_order'] if 'sort_order' in request.GET else None
        if sort_order:
            if '-' in sort_order:
                artifacts = artifacts.order_by(
                    F(sort_order[1:]).desc(nulls_last=True))
            else:
                artifacts = artifacts.order_by(
                    F(sort_order).asc(nulls_first=True))

        page = int(request.GET['page']) if 'page' in request.GET else 1
        count = artifacts.count()
        PER_PAGE = 10
        start = PER_PAGE * (page - 1)
        end = start + 10
        serializer = ArtifactSerializer(
            artifacts[start:min(end, count)], many=True)

        return {
            'count': count,
            'page': page,
            'data': serializer.data,
        }

    # filters here
    if filters:
        proper_filters = filter_artifacts(filters)
        artifacts = artifacts.filter(**proper_filters)

    serializer = ArtifactSerializer(artifacts[:10], many=True)

    return {
        'count': artifacts.count(),
        'page': 1,
        'data': serializer.data,
    }


def filter_siege(filters):
    proper_filters = {}
    for key, val in filters:
        if key in ['monsters__base_monster', 'leader__base_monster', 'wizard__guild__siege_ranking']:
            proper_filters[key + '__in'] = val
        elif key in ['ratio', 'win', 'lose']:
            proper_val = [float(v) for v in val]
            proper_val.sort()
            proper_filters[key + '__gte'] = proper_val[0]
            proper_filters[key + '__lte'] = proper_val[1]
    return proper_filters


def get_siege_table(request, filters=None):
    sieges = SiegeRecord.objects.all().select_related('wizard', 'wizard__guild', 'leader', 'leader__base_monster', 'leader__base_monster__family').prefetch_related(
        'monsters',
        'monsters__base_monster',
        'monsters__base_monster__family',
        'monsters__runes',
        'monsters__runes_rta',
        'monsters__runes__rune_set',
        'monsters__runes_rta__rune_set',
        'monsters__artifacts',
        'monsters__artifacts_rta',
        'leader__runes',
        'leader__runes__rune_set',
        'leader__runes_rta',
        'leader__runes_rta__rune_set',
        'leader__artifacts',
        'leader__artifacts_rta'
    ).defer(
        'last_update', 'full', ).filter(full=True).order_by()

    if request:  # ajax call on page change
        filters = list(request.GET.lists())

        proper_filters = filter_siege(filters)
        sieges = sieges.filter(**proper_filters)

        sort_order = request.GET['sort_order'] if 'sort_order' in request.GET else None
        if sort_order:
            if '-' in sort_order:
                sieges = sieges.order_by(
                    F(sort_order[1:]).desc(nulls_last=True))
            else:
                sieges = sieges.order_by(
                    F(sort_order).asc(nulls_first=True))

        page = int(request.GET['page']) if 'page' in request.GET else 1
        count = sieges.count()
        PER_PAGE = 10
        start = PER_PAGE * (page - 1)
        end = start + 10
        serializer = SiegeSerializer(
            sieges[start:min(end, count)], many=True)

        return {
            'count': count,
            'page': page,
            'data': serializer.data,
        }

    # filters here
    if filters:
        proper_filters = filter_siege(filters)
        sieges = sieges.filter(**proper_filters)

    serializer = SiegeSerializer(sieges[:10], many=True)

    return {
        'count': sieges.count(),
        'page': 1,
        'data': serializer.data,
    }


def get_cairos_distribution(runs, parts):
    """Return sets of clear times in specific number of parts, to make Distribution chart."""
    runs_seconds = [run['clear_time'].total_seconds()
                    for run in runs if run['win']]
    if not len(runs_seconds):
        return []

    fastest = min(runs_seconds)
    slowest = max(runs_seconds)

    delta = (slowest - fastest) / (parts + 1)
    delta = max(1, delta)
    points = np.arange(fastest, slowest + delta, delta)

    distribution = np.histogram(runs_seconds, bins=points)[0].tolist()

    points = [str(timedelta(seconds=round((points[i] + points[i+1])/2)))
              for i in range(len(points) - 1)]

    return [{
        'name': p,
        'count': d,
    } for p, d in zip(points, distribution)]


def filter_cairos_detail(filters):
    proper_filters = {}
    for key, val in filters:
        if key in ['monsters__base_monster', ]:
            proper_filters[key + '__in'] = val
    return proper_filters


def filter_dimhole_detail(filters):
    proper_filters = {}
    for key, val in filters:
        if key in ['monsters__base_monster', ]:
            proper_filters[key + '__in'] = val
        elif key in ['practice']:
            proper_filters[key] = val[0] == 'true'

    return proper_filters


def filter_raid_detail(filters):
    proper_filters = {}
    for key, val in filters:
        if key == 'leader':
            proper_filters[key + '__base_monster_id__in'] = val
    return proper_filters


def filter_rift_detail(filters):
    proper_filters = {}
    for key, val in filters:
        if key == 'leader':
            proper_filters[key + '__base_monster_id__in'] = val
        elif key == 'dmg_total':
            proper_val = [float(v) for v in val]
            proper_val.sort()
            proper_filters[key + '__gte'] = proper_val[0]
            proper_filters[key + '__lte'] = proper_val[1]
    return proper_filters


def get_rift_distribution(runs, parts):
    """Return sets of damages in specific number of parts, to make Distribution chart."""
    damages = [r for r in runs if r is not None]

    if not len(damages):
        return []

    lowest = min(damages)
    highest = max(damages)

    delta = (highest - lowest) / (parts + 1)
    delta = max(1, delta)
    points = np.arange(lowest, highest + delta, delta)

    distribution = np.histogram(damages, bins=points)[0].tolist()

    points = [str(int((points[i] + points[i+1])/2))
              for i in range(len(points) - 1)]

    return [{
        'name': p,
        'count': d,
    } for p, d in zip(points, distribution)]


def get_series_distribution(series, parts):
    """Return sets of series values in specific number of parts, to make Distribution chart."""
    if not len(series):
        return []
    hist = series.values

    minimum = min(hist)
    maximum = max(hist)

    delta = (maximum - minimum) / (parts + 1)
    delta = max(1, delta)
    points = np.arange(minimum, maximum + delta, delta)

    distribution = np.histogram(hist, bins=points)[0].tolist()

    points = [str(int((points[i] + points[i+1])/2))
              for i in range(len(points) - 1)]

    return [{
        'name': p,
        'count': d,
    } for p, d in zip(points, distribution)]


def _unzip_get_params(params):
    x = dict()
    for k, v in params:
        if isinstance(v, dict):
            x[k] = _unzip_get_params(v)
        elif isinstance(v, list):
            for i, vi in enumerate(v):
                x[f'{k}{i}'] = vi
        else:
            x[k] = v
    return x


def calculate_cache_key(view_instance, view_method, request, args, kwargs):
    key_builder = [view_instance.__class__.__name__, request.method, ]
    if request.GET:
        t = [f'{k}={v}' for k, v in _unzip_get_params(
            list(request.GET.lists())).items()]
        t.sort()
        key_builder += t
    if kwargs:
        t = [f'{k}={v}' for k, v in kwargs.items()]
        t.sort()
        key_builder += t
    if args:
        t = list(args)
        t.sort()
        key_builder += t

    return '.'.join(key_builder)


def parse_wizard(wizard, dim_hole_energy):
    return {
        'name': wizard['wizard_name'],
        'country': wizard['wizard_last_country'],
        'level': wizard['wizard_level'],
        'mana': wizard['wizard_mana'],
        'crystals': wizard['wizard_crystal'],
        'guild_points': wizard['guild_point'],
        'glory_points': wizard['honor_point'],
        'rta_points': wizard['honor_medal'],
        'shapeshifting_stones': wizard['costume_point'],
        'social_points': wizard['social_point_current'],
        'ancient_coins': wizard['event_coin'],
        'energy': wizard['wizard_energy'],
        'energy_max': wizard['energy_max'],
        'dim_hole_energy': dim_hole_energy,
        'arena_wings': wizard['arena_energy'],
        'dim_rift_crystals': wizard['darkportal_energy'],
    }


def parse_monsters(monsters, locked_monsters):
    # monsters[id]['attribute']
    attributes = dict(MonsterBase.MONSTER_ATTRIBUTES)
    # monsters[id]['unit_master_id'][MonsterBase MODEL]
    archetypes = dict(MonsterBase.MONSTER_TYPES)

    monsters_fusion = MonsterFusion.objects.all()
    monsters_hoh = MonsterHoh.objects.all()

    base_monsters = list(set([monster['unit_master_id']
                              for monster in monsters]))
    base_monsters = {mb['id']: mb for mb in MonsterBase.objects.defer('family').filter(id__in=base_monsters).values(
        'id', 'name', 'archetype', 'attribute', 'awaken', 'base_class').order_by()}

    base_stars = {
        'star_1': [1, 0],
        'star_2': [2, 0],
        'star_3': [3, 0],
        'star_4': [4, 0],
        'star_5': [5, 0],
    }

    monster_elements = dict()
    monster_archetypes = dict()
    for val in attributes.values():
        if val not in monster_elements:
            monster_elements[val] = 0
    for val in archetypes.values():
        if val not in monster_archetypes:
            monster_archetypes[val] = 0

    nat5_non_fusion = list()
    ld_nat4plus_non_fusion_nor_hoh = list()
    for monster in monsters:
        base_monster = base_monsters[monster['unit_master_id']]
        monster_elements[attributes[monster['attribute']]] += 1
        monster_archetypes[archetypes[base_monster['archetype']]] += 1
        base_stars['star_' + str(base_monster['base_class'])][1] += 1
        if base_monster['base_class'] == 5:
            if not monsters_fusion.filter(monster=base_monster['id']).exists():
                nat5_non_fusion.append({
                    'monster': base_monster['name'],
                    'acquiration_date': monster['create_time'],
                })
        if monster['attribute'] >= 4 and base_monster['base_class'] >= 4:  # l&d, 4*+
            if not monsters_hoh.filter(monster=base_monster['id']).exists() and not monsters_fusion.filter(monster=base_monster['id']).exists():
                ld_nat4plus_non_fusion_nor_hoh.append({
                    'monster': base_monster['name'],
                    'acquiration_date': monster['create_time'],
                })

    last_nat5 = sorted(nat5_non_fusion, key=itemgetter(
        'acquiration_date'), reverse=True)[0] if nat5_non_fusion else {}
    last_nat4_ld = sorted(ld_nat4plus_non_fusion_nor_hoh, key=itemgetter(
        'acquiration_date'), reverse=True)[0] if ld_nat4plus_non_fusion_nor_hoh else {}

    return {
        'count': len(monsters),
        'elements': monster_elements,
        'archetypes': monster_archetypes,
        'base_class': base_stars,

        'nat5_not_fusion': nat5_non_fusion,
        'last_nat5': (datetime.datetime.today() - datetime.datetime.strptime(last_nat5['acquiration_date'], "%Y-%m-%d %H:%M:%S")).days if nat5_non_fusion else None,

        'ld4plus_not_fusion': ld_nat4plus_non_fusion_nor_hoh,
        'last_ld4plus': (datetime.datetime.today() - datetime.datetime.strptime(last_nat4_ld['acquiration_date'], "%Y-%m-%d %H:%M:%S")).days if ld_nat4plus_non_fusion_nor_hoh else None,
    }


def parse_runes(runes_unequipped, runes_equipped, runes_locked):
    # unpack both and create one list
    runes = [*runes_unequipped, *runes_equipped]

    # only current efficiency
    efficiencies = [calc_efficiency(rune)[0] for rune in runes]
    eff_min = min(efficiencies)
    eff_max = max(efficiencies)
    eff_mean = round(statistics.mean(efficiencies), 2)
    eff_median = round(statistics.median(efficiencies), 2)
    eff_st_dev = round(statistics.stdev(efficiencies), 2)
    maxed = len([True for rune in runes if rune['upgrade_curr'] == 15])

    runes_len = len(runes)
    runes_unequipped_len = len(runes_unequipped)
    runes_equipped_len = len(runes_equipped)
    runes_locked_len = len(runes_locked)

    sets = {row['id']: [row['name'].lower(), 0] for row in RuneSet.objects.values(
        'id', 'name') if row['id'] != 99}  # all sets except immemorial
    slots = {
        'slot_1': [1, 0],
        'slot_2': [2, 0],
        'slot_3': [3, 0],
        'slot_4': [4, 0],
        'slot_5': [5, 0],
        'slot_6': [6, 0],
    }

    for rune in runes:
        sets[rune['set_id']][1] += 1
        slots['slot_' + str(rune['slot_no'])][1] += 1

    return {
        'count': runes_len,
        'unequipped_count': runes_unequipped_len,
        'unequipped_percentage': round(runes_unequipped_len * 100 / runes_len, 2),
        'equipped_count': runes_equipped_len,
        'equipped_percentage': round(runes_equipped_len * 100 / runes_len, 2),
        'locked_count': runes_locked_len,
        'locked_percentage': round(runes_locked_len * 100 / runes_len, 2),

        'eff_min': eff_min,
        'eff_max': eff_max,
        'eff_mean': eff_mean,
        'eff_median': eff_median,
        'eff_st_dev': eff_st_dev,

        'maxed': maxed,
        'maxed_percentage': round(maxed * 100 / runes_len, 2),

        'sets': sets,
        'slots': slots,
    }


def parse_guild_members(guild_members, guild_member_defenses):
    members = list()
    for temp_member in guild_members.keys():
        member = guild_members[temp_member]
        defenses = [row['unit_list']
                    for row in guild_member_defenses if row['wizard_id'] == member['wizard_id']][0]
        if defenses:
            defense_1 = len(defenses[0])
            defense_2 = len(defenses[1])
        else:
            defense_1 = 0
            defense_2 = 0

        last_login = datetime.datetime.utcfromtimestamp(
            member['last_login_timestamp'])
        members.append({
            'name': member['wizard_name'],
            'joined': datetime.datetime.utcfromtimestamp(member['join_timestamp']),
            'last_login': last_login,
            'last_login_days': (datetime.datetime.today() - last_login).days,
            'defense_1': defense_1,
            'defense_2': defense_2,
        })

        members = sorted(members, key=itemgetter(
            'last_login'), reverse=True)
    return members


def parse_guild(guild, ranking, guild_member_defenses):
    guild_info = guild['guild_info']

    gw_members_count = len(guild_member_defenses)
    gw_members_defense_count = 0
    for wizard in guild_member_defenses:
        for defense in wizard['unit_list']:
            gw_members_defense_count += len(defense)

    gw_ranks = dict(Guild.GUILD_RANKS)

    return {
        'name': guild_info['name'],
        'master': guild_info['master_wizard_name'],
        'best_ranking': gw_ranks[ranking['best']['rating_id']],
        'current_ranking': gw_ranks[ranking['current']['rating_id']],
        'members_count': guild_info['member_now'],
        'members_max': guild_info['member_max'],
        'members_gw': gw_members_count,
        'defenses_count': gw_members_defense_count,
        # 2 defenses and 3 monsters per defense
        'defenses_max': gw_members_count * 2 * 3,
        'members': parse_guild_members(guild['guild_members'], guild_member_defenses),
    }


def parse_friends(friend_list):
    friends = list()
    mons = list()
    for friend in friend_list:
        last_login = datetime.datetime.utcfromtimestamp(
            friend['last_login_timestamp'])
        friends.append({
            'name': friend['wizard_name'],
            'last_login': last_login,
            'last_login_days': (datetime.datetime.today() - last_login).days,
            'rep': {
                'monster': friend['rep_unit_master_id'],
                'image': None,
                'level': friend['rep_unit_level'],
                'stars': friend['rep_unit_class'],
            },
        })
        mons.append(friend['rep_unit_master_id'])

    mons = list(set(mons))
    mons = {mb.id: mb for mb in MonsterBase.objects.select_related(
        'family').filter(id__in=mons)}
    for friend in friends:
        mon_id = friend['rep']['monster']
        friend['rep']['monster'] = f'{mons[mon_id].name} ({mons[mon_id].family.name})' if mons[
            mon_id].awaken > 0 else mons[mon_id].name
        friend['rep']['image'] = mons[mon_id].get_image()

    friends = sorted(friends, key=itemgetter('last_login'), reverse=True)

    return friends


def generate_bot_monster_report(monster_id):
    monsters = Monster.objects.filter(base_monster_id=monster_id, stars=6, level=40).prefetch_related(
        'runes', 'runes__rune_set',
        'artifacts',
    ).order_by('id').values(
        'id', 'skills', 'transmog', 'locked', 'storage',
        'hp', 'attack', 'defense', 'speed', 'res', 'acc', 'crit_rate', 'crit_dmg', 'avg_eff_total', 'eff_hp',
        'runes__slot', 'runes__rune_set__name', 'runes__primary',
        'artifacts__rtype', 'artifacts__primary', 'artifacts__substats',
    )

    # base monster info, to serialize with MonsterBaseSerializer
    try:
        base_monster = MonsterBase.objects.get(id=monster_id)
    except MonsterBase.DoesNotExist:
        return None
    monster = MonsterBaseSerializer(base_monster).data

    monster_hoh = MonsterHoh.objects.filter(
        id=(str(monster_id)[:4] + '0' + str(monster_id)[-1])).order_by('-date_open')
    if monster_hoh.exists():
        monster['hoh'] = monster_hoh.first().start_date.strftime("YYYY-mm-dd")
    else:
        monster['hoh'] = 'No'

    monster['fusion'] = 'Yes' if MonsterFusion.objects.filter(
        id=(str(monster_id)[:4] + '0' + str(monster_id)[-1])).exists() else 'No'
    # family info, to serialize with MonsterBaseSerializer
    family_monsters = MonsterBase.objects.filter(family_id=base_monster.family_id).exclude(
        id=monster_id).select_related('family').order_by('id')

    proper_records = []
    rune_sets = {rs.name: rs.amount for rs in RuneSet.objects.all()}
    rune_sets = {k: v for k, v in sorted(
        rune_sets.items(), key=lambda item: item[1], reverse=True)}
    rune_effects = dict(Rune.RUNE_EFFECTS)
    artifact_substats = dict(Artifact.ARTIFACT_EFFECTS_ALL)
    stats = ['hp', 'attack', 'defense', 'speed', 'res', 'acc',
             'crit_rate', 'crit_dmg', 'avg_eff_total', 'eff_hp', ]
    pie_stats = ['transmog', 'locked', 'storage', ]
    to_cpy = [
        'id', 'skills'
    ] + pie_stats + stats
    sets_4 = {s: 0 for s in ['Violent', 'Swift',
                             'Rage', 'Fatal', 'Despair', 'Vampire']}

    # prepare records for DataFrame
    record_groups = itertools.groupby(monsters, lambda m: m['id'])
    for _, record_group in record_groups:
        records = list(record_group)

        data = {}

        sets = []
        for record in records:
            if not data.keys():
                for item in to_cpy:
                    data[item] = record[item]

            # some trash records, looking only for monsters with equipped runes
            if not record['runes__slot']:
                continue
            slot = record['runes__slot'] - 1
            if f'rune_{slot + 1}' not in data:
                if record['runes__primary']:
                    data[f'rune_{slot + 1}'] = rune_effects[record['runes__primary']]
                if record['runes__rune_set__name']:
                    sets.append(record['runes__rune_set__name'])

            if record['artifacts__rtype']:
                a_type = Artifact.get_artifact_rtype(
                    record['artifacts__rtype']).lower()
                if f'artifact_{a_type}' not in data:
                    if record['artifacts__primary']:
                        data[f'artifact_{a_type}'] = Artifact.get_artifact_primary(
                            record['artifacts__primary'])
                    if 'artifact_substats' not in data:
                        data['artifact_substats'] = []
                    if record['artifacts__substats']:
                        data['artifact_substats'] += [artifact_substats[r]
                                                      for r in record['artifacts__substats']]

        if all([True if f'rune_{i}' in data else False for i in range(1, 7)]):
            proper_sets = {}
            sets_str = []
            full = 0
            for s in sets:
                if s not in proper_sets:
                    proper_sets[s] = 0
                proper_sets[s] += 1
            for s in proper_sets:
                occ = math.floor(proper_sets[s] / rune_sets[s])
                if occ:
                    full += rune_sets[s] * occ
                    if rune_sets[s] == 4:  # add 4-rune sets at first place
                        sets_4[s] += 1
                        sets_str.insert(0, s)
                    else:
                        sets_str.append(s)
            data['sets'] = ' + '.join(sets_str)
            if full != 6:
                data['sets'] += ' + Broken'

            if 'artifact_attribute' not in data:
                data['artifact_attribute'] = None
            if 'artifact_archetype' not in data:
                data['artifact_archetype'] = None
            if 'artifact_substats' not in data:
                data['artifact_substats'] = []
            proper_records.append(data)

    df = pd.DataFrame(proper_records)

    if not df.shape[0]:  # empty df
        monster['build'] = 'No information given'
        monster['sets'] = [{
            'name': f'Top {i + 1} set',
            'text': 'No information given'
        } for i in range(3)]
        content = {
            'chart_data': {
                'dist_acc': [],
                'dist_attack': [],
                'dist_avg_eff_total': [],
                'dist_crit_dmg': [],
                'dist_crit_rate': [],
                'dist_defense': [],
                'dist_eff_hp': [],
                'dist_hp': [],
                'dist_res': [],
                'dist_speed': [],
                'pie_locked': [],
                'pie_skilled_up': [],
                'pie_storage': [],
                'pie_transmog': [],
                'vc_artifact_primary': [],
                'vc_artifact_substats': [],
                'vc_rune_builds': [],
                'vc_rune_slots': [],
                'vc_sets': [],
                'vc_sets_4': [],
            },
            'monster': monster,
            'family': MonsterBaseSerializer(family_monsters, many=True).data,
            'table': [],
            'desc': {},
        }

        return content

    chart_data = {}
    # distribution charts
    for stat in stats:
        chart_data[f'dist_{stat}'] = get_series_distribution(
            df[stat], 15)

    # pie charts
    for stat in pie_stats:
        chart_data[f'pie_{stat}'] = [{'name': 'Yes' if k else 'No', 'count': v}
                                     for k, v in df[stat].value_counts().to_dict().items()]
    chart_data['pie_skilled_up'] = [{'name': 'Yes' if k else 'No', 'count': v}
                                    for k, v in (df['skills'].apply(lambda x: (np.array(x) == np.array(base_monster.max_skills)).all())).value_counts().to_dict().items()]

    # bar charts
    chart_data['vc_sets'] = [{'name': k, 'count': v}
                             for k, v in df['sets'].value_counts().to_dict().items() if v > 10]
    chart_data['vc_sets_4'] = sorted([{'name': k, 'count': v}
                                      for k, v in sets_4.items()], key=lambda x: x['count'], reverse=True)

    vc_rune_slot_2 = df['rune_2'].dropna().value_counts().to_dict()
    vc_rune_slot_4 = df['rune_4'].dropna().value_counts().to_dict()
    vc_rune_slot_6 = df['rune_6'].dropna().value_counts().to_dict()
    rune_unique_slot = list(
        set(list(vc_rune_slot_2.keys()) + list(vc_rune_slot_4.keys()) + list(vc_rune_slot_6.keys())))
    chart_data['vc_rune_slots'] = []
    for s in rune_unique_slot:
        chart_data['vc_rune_slots'].append({
            "name": s,
            "Slot 2": vc_rune_slot_2[s] if s in vc_rune_slot_2 else 0,
            "Slot 4": vc_rune_slot_4[s] if s in vc_rune_slot_4 else 0,
            "Slot 6": vc_rune_slot_6[s] if s in vc_rune_slot_6 else 0,
        })

    vc_artifact_element_primary = df['artifact_attribute'].dropna(
    ).value_counts().to_dict()
    vc_artifact_archetype_primary = df['artifact_archetype'].dropna(
    ).value_counts().to_dict()
    artifact_unique_primary = list(set(list(
        vc_artifact_archetype_primary.keys()) + list(vc_artifact_element_primary.keys())))
    chart_data['vc_artifact_primary'] = []
    for s in artifact_unique_primary:
        chart_data['vc_artifact_primary'].append({
            "name": s,
            "Element": vc_artifact_element_primary[s] if s in vc_artifact_element_primary else 0,
            "Archetype": vc_artifact_archetype_primary[s] if s in vc_artifact_archetype_primary else 0,
        })

    # most common builds
    builds_count = df.groupby(["rune_2", "rune_4", "rune_6"]).size().reset_index(
        name='count').sort_values(["count"], ascending=False)
    builds_count['name'] = builds_count['rune_2'] + ' / ' + \
        builds_count['rune_4'] + ' / ' + builds_count['rune_6']
    builds_count = builds_count[builds_count['count'] > 10][['name', 'count']]
    chart_data['vc_rune_builds'] = builds_count.to_dict(orient='records')

    # artifact substats bar chart
    artifact_subs_series = []
    _ = df['artifact_substats'].dropna().apply(
        lambda li: [artifact_subs_series.append(l) for l in li])
    artifact_subs_series = pd.Series(artifact_subs_series)
    chart_data['vc_artifact_substats'] = [{'name': k, 'count': v}
                                          for k, v in artifact_subs_series.dropna().value_counts().to_dict().items() if v > 10]

    monster['build'] = chart_data['vc_rune_builds'][0]['name'] if chart_data['vc_rune_builds'] else 'No information given'
    monster['sets'] = [{
        'name': f'Top {i + 1} set',
        'text': f"{chart_data['vc_sets'][i]['name']} ({round(chart_data['vc_sets'][i]['count'] / df.shape[0] * 100)}%)" if len(chart_data['vc_sets']) > i else 'No information given'
    } for i in range(3)]

    df_stats = df[stats].describe().drop(['count', ], axis=0).round(2)
    df_stats.columns = ['HP', 'Attack', 'Defense',
                        'Speed', 'Resistance', 'Accuracy', 'Critical Rate', 'Critical Damage', 'Average Efficiency', 'Effective HP']

    content = {
        'chart_data': chart_data,
        'monster': monster,
        'family': MonsterBaseSerializer(family_monsters, many=True).data,
        'table': df.fillna('').to_dict(orient='records'),
        'desc': df_stats.fillna('-').to_dict('index'),
    }

    return content