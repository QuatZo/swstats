import pandas as pd
import numpy as np
import datetime
import math
import time

from django.db.models import F, Q, Avg, Min, Max, Sum, Count, FloatField, Func

from website.models import *
from .serializers import RuneFullSerializer, MonsterSerializer


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


def get_scoring_for_profile(wizard_id):
    start = time.time()
    points = get_scoring_system()
    wiz = Wizard.objects.get(id=wizard_id)
    runes = Rune.objects.filter(wizard=wiz)
    monsters = Monster.objects.filter(wizard=wiz).prefetch_related(
        'base_monster', 'runes', 'artifacts')
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
    a_b_max_count = a_b.filter(level=10).count()
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

    return points


def calc_monster_comparison_stats(id_, hp, attack, defense, speed, res, acc, crit_rate, crit_dmg, avg_eff_total, eff_hp, df_group, df_group_len, df_means):
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
        'img_url': Monster.objects.get(id=id_).get_image(),
        'rank': dict()
    }
    for key, val in kw.items():
        m_stats['rank'][key] = {
            'top': round(len(df_group[df_group[key] > val]) / df_group_len * 100, 2),
            'avg': val - df_means[key],
            'val': val,
        }

        if key == 'avg_eff_total':
            m_stats['rank'][key]['avg'] = round(m_stats['rank'][key]['avg'], 2)
        else:
            m_stats['rank'][key]['avg'] = int(
                round(m_stats['rank'][key]['avg']))

    return m_stats


def calc_rune_comparison_stats(id_, hp_f, hp, atk_f, atk, def_f, def_, spd, res, acc, c_rate, c_dmg, eff, df_group, df_group_len, df_means):
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
    rune_obj = Rune.objects.get(id=id_)
    r_stats = {
        'id': id_,
        'img_url': rune_obj.get_full_image(),
        'mainstat': rune_obj.get_primary_display(),
        'rank': dict()
    }
    for key, val in kw.items():
        r_stats['rank'][key] = {
            'top': round(len(df_group[df_group[key] > val]) / df_group_len * 100, 2) if val else None,
            'avg': val - df_means[key] if val else None,
            'val': val if val else None,
        }
        if key == 'efficiency':
            r_stats['rank'][key]['avg'] = round(r_stats['rank'][key]['avg'], 2)
        elif r_stats['rank'][key]['avg']:
            r_stats['rank'][key]['avg'] = int(
                round(r_stats['rank'][key]['avg']))

    return r_stats


def get_profile_comparison_with_database(wizard_id):
    monsters = Monster.objects.select_related('base_monster', 'base_monster__family', ).exclude(base_monster__archetype=5).exclude(base_monster__archetype=0).filter(
        stars=6).order_by('base_monster__name')  # w/o material, unknown; only 6*
    monsters_cols = ['id', 'wizard__id', 'base_monster__name', 'hp', 'attack', 'defense', 'speed',
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
    runes_cols = ['id', 'wizard__id', 'slot', 'rune_set__id', 'primary', 'efficiency',
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
        comparison['monsters'] += [calc_monster_comparison_stats(*row, df_group, len(df_group), df_means) for row in zip(df_wiz['id'], df_wiz['hp'], df_wiz['attack'], df_wiz['defense'],
                                                                                                                         df_wiz['speed'], df_wiz['res'], df_wiz['acc'], df_wiz['crit_rate'], df_wiz['crit_dmg'], df_wiz['avg_eff_total'], df_wiz['eff_hp'])]

    df_groups = df_runes.groupby(['slot', 'rune_set__id', 'primary'])
    for _, df_group in df_groups:
        df_wiz = df_group[df_group['wizard__id'] == wizard_id]
        df_means = df_group.mean()
        comparison['runes'] += [calc_rune_comparison_stats(*row, df_group, len(df_group), df_means) for row in zip(df_wiz['id'], df_wiz['sub_hp_flat'], df_wiz['sub_hp'], df_wiz['sub_atk_flat'],
                                                                                                                   df_wiz['sub_atk'], df_wiz['sub_def_flat'], df_wiz['sub_def'], df_wiz['sub_speed'], df_wiz['sub_res'], df_wiz['sub_acc'], df_wiz['sub_crit_rate'], df_wiz['sub_crit_dmg'], df_wiz['efficiency'])]

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
    monsters = Monster.objects.all().select_related('base_monster', 'base_monster__family', ).prefetch_related(
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
