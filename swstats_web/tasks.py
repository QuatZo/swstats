from django.db.models import Count, Q, F, Avg, StdDev, Min, Max

from website.celery import app as celery_app
from website.tasks import handle_profile_upload_task
from website.models import Rune, RuneSet, Monster, MonsterBase, Artifact, SiegeRecord, Guild, DungeonRun, DimensionHoleRun, RaidDungeonRun, RiftDungeonRun, MonsterHoh, MonsterFusion
from .functions import *
from .serializers import MonsterImageSerializer, MonsterBaseSerializer
from .aggregations import Perc25, Median, Perc75

import itertools
import operator
from datetime import timedelta
import math
import pandas as pd
import numpy as np


@celery_app.task(name="profile.compare", bind=True)
def handle_profile_upload_and_rank_task(self, data):
    self.update_state(state='PROGRESS', meta={'step': 'Creating profile'})
    handle_profile_upload_task.s(data).apply()
    self.update_state(state='PROGRESS', meta={
                      'step': 'Comparing profile to database'})

    content = {
        'points': get_scoring_for_profile(data['wizard_info']['wizard_id']),
        'comparison': get_profile_comparison_with_database(data['wizard_info']['wizard_id'])
    }

    return content


@celery_app.task(name='fetch.runes', bind=True)
def fetch_runes_data(self, filters):
    runes = Rune.objects.all().select_related('rune_set', ).defer(
        'wizard', 'base_value', 'sell_value').order_by()

    # filters here
    proper_filters = filter_runes(filters)
    runes = runes.filter(**proper_filters)

    # prepare filters to show in Form
    form_filters = Rune.get_filter_fields()
    #

    stars = runes.values('stars').annotate(count=Count('stars'))
    rune_stars = {}
    for star in stars:
        s_c = star['stars'] % 10  # Ancient runes
        if s_c not in rune_stars:
            rune_stars[s_c] = {
                'name': s_c,
                'count': 0,
            }
        rune_stars[s_c]['count'] += star['count']

    qualities = runes.values('quality').annotate(count=Count('quality'))
    qualities_orig = runes.values('quality_original').annotate(
        count=Count('quality_original'))
    rune_qualities = {}
    for q in qualities:
        q_n = Rune.get_rune_quality(q['quality']).replace('Ancient ', '')
        if q_n not in rune_qualities:
            rune_qualities[q_n] = {
                'name': q_n,
                'count': 0,
                'original': 0,
            }
        rune_qualities[q_n]['count'] += q['count']
    for q in qualities_orig:
        q_n = Rune.get_rune_quality(
            q['quality_original']).replace('Ancient ', '')
        if q_n not in rune_qualities:
            rune_qualities[q_n] = {
                'name': q_n,
                'count': 0,
                'original': 0,
            }
        rune_qualities[q_n]['original'] += q['count']

    primary = runes.values('primary').annotate(count=Count('primary'))
    rune_primaries = {}
    for p in primary:
        p_n = Rune.get_rune_primary(p['primary'])
        rune_primaries[p_n] = {
            'name': p_n,
            'count': p['count'],
        }

    content = {
        'chart_data': {
            'rune_set': [{
                'name': rune_set['rune_set__name'],
                'count': rune_set['count'],
            } for rune_set in runes.values('rune_set__name').annotate(count=Count('rune_set__name'))],
            'rune_slot': [{
                'name': rune_slot['slot'],
                'count': rune_slot['count'],
            } for rune_slot in runes.values('slot').annotate(count=Count('slot'))],
            'rune_level': [{
                'name': rune_level['upgrade_curr'],
                'count': rune_level['count'],
            } for rune_level in runes.values('upgrade_curr').annotate(count=Count('upgrade_curr'))],
            'rune_stars': list(rune_stars.values()),
            'rune_qualities': list(rune_qualities.values()),
            'rune_primaries': list(rune_primaries.values()),
        },
        'filters': form_filters,
        'table': get_runes_table(None, filters)
    }

    return content


@celery_app.task(name='fetch.monsters', bind=True)
def fetch_monsters_data(self, filters):
    monsters = Monster.objects.exclude(base_monster__archetype__in=[0, 5]).select_related('base_monster', 'base_monster__family', ).defer(
        'wizard', 'source', 'transmog', 'runes', 'runes_rta', 'artifacts', 'artifacts_rta', ).order_by()

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

    # prepare filters to show in Form
    form_filters = Monster.get_filter_fields()
    #

    stars = monsters.values('stars').annotate(count=Count('stars'))
    base_stars = monsters.values('base_monster__base_class').annotate(
        count=Count('base_monster__base_class'))
    monster_stars = {}

    for s in stars:
        s_n = s['stars']
        if s_n not in monster_stars:
            monster_stars[s_n] = {
                "name": s_n,
                "count": 0,
                "natural": 0,
            }
        monster_stars[s_n]["count"] = s["count"]

    for s in base_stars:
        s_n = s['base_monster__base_class']
        if s_n not in monster_stars:
            monster_stars[s_n] = {
                "name": s_n,
                "count": 0,
                "natural": 0,
            }
        monster_stars[s_n]["natural"] = s["count"]

    elements = monsters.values('base_monster__attribute').annotate(
        count=Count('base_monster__attribute'))
    monster_elements = {}
    for e in elements:
        e_n = MonsterBase.get_attribute_name(e['base_monster__attribute'])
        monster_elements[e_n] = {
            "name": e_n,
            "count": e['count']
        }

    archetypes = monsters.values('base_monster__archetype').annotate(
        count=Count('base_monster__archetype'))
    monster_archetypes = {}
    for e in archetypes:
        e_n = MonsterBase.get_archetype_name(e['base_monster__archetype'])
        monster_archetypes[e_n] = {
            "name": e_n,
            "count": e['count']
        }

    awakens = monsters.values('base_monster__awaken').annotate(
        count=Count('base_monster__awaken'))
    monster_awakens = {}
    for e in awakens:
        e_n = MonsterBase.get_awaken_name(e['base_monster__awaken'])
        monster_awakens[e_n] = {
            "name": e_n,
            "count": e['count']
        }

    stats = {
        'hp': 'HP',
        'attack': 'Attack',
        'defense': 'Defense',
        'speed': 'Speed',
        'res': 'Resistance',
        'acc': 'Accuracy',
        'crit_rate': 'Critical Rate',
        'crit_dmg': 'Critical Damage',
        'avg_eff_total': 'Average Efficiency',
        'eff_hp': 'Effective HP',
    }

    agg = []
    for stat in stats.keys():
        agg += [
            Avg(stat),
            StdDev(stat),
            Min(stat),
            Perc25(stat),
            Median(stat),
            Perc75(stat),
            Max(stat)
        ]

    desc = {}
    for key, val in monsters.aggregate(*agg).items():
        stat, f = key.split('__')
        if f == 'perc25':
            f = '25%'
        elif f == 'median':
            f = '50%'
        elif f == 'perc75':
            f = '75%'
        elif f == 'stdded':
            f = 'std'
        if f not in desc:
            desc[f] = {}
        desc[f][stats[stat]] = round(val, 2)

    content = {
        'chart_data': {
            'monster_elements': list(monster_elements.values()),
            'monster_archetypes': list(monster_archetypes.values()),
            'monster_awakens': list(monster_awakens.values()),
            'monster_stars': list(monster_stars.values()),
        },
        'desc': desc,
        'filters': form_filters,
        'table': get_monsters_table(None, filters)
    }

    return content


@celery_app.task(name='fetch.artifacts', bind=True)
def fetch_artifacts_data(self, filters):
    artifacts = Artifact.objects.all().defer('wizard').order_by()

    # filters here
    proper_filters = filter_artifacts(filters)
    artifacts = artifacts.filter(**proper_filters)

    # prepare filters to show in Form
    form_filters = Artifact.get_filter_fields()
    #

    qualities = artifacts.values('quality').annotate(count=Count('quality'))
    qualities_orig = artifacts.values('quality_original').annotate(
        count=Count('quality_original'))
    artifact_qualities = {}
    for q in qualities:
        q_n = Artifact.get_artifact_quality(q['quality'])
        if q_n not in artifact_qualities:
            artifact_qualities[q_n] = {
                'name': q_n,
                'count': 0,
                'original': 0,
            }
        artifact_qualities[q_n]['count'] += q['count']
    for q in qualities_orig:
        q_n = Artifact.get_artifact_quality(q['quality_original'])
        if q_n not in artifact_qualities:
            artifact_qualities[q_n] = {
                'name': q_n,
                'count': 0,
                'original': 0,
            }
        artifact_qualities[q_n]['original'] += q['count']

    primary = artifacts.values('primary').annotate(count=Count('primary'))
    artifact_primaries = []
    for p in primary:
        p_n = Artifact.get_artifact_primary(p['primary'])
        artifact_primaries.append({
            'name': p_n,
            'count': p['count'],
        })

    rtype = artifacts.values('rtype').annotate(count=Count('rtype'))
    artifact_rtypes = []
    for r in rtype:
        r_n = Artifact.get_artifact_rtype(r['rtype'])
        artifact_rtypes.append({
            'name': r_n,
            'count': r['count'],
        })

    slot_attr = artifacts.filter(attribute__isnull=False, attribute__gt=0).values(
        'rtype', 'attribute').annotate(count=Count('attribute'))
    slot_el = artifacts.filter(archetype__isnull=False, archetype__gt=0).values(
        'rtype', 'archetype').annotate(count=Count('archetype'))
    artifact_slots = []
    for s in slot_attr:
        s_n = Artifact.get_artifact_slot(s['rtype'], s['attribute'])
        artifact_slots.append({
            "name": s_n,
            "count": s["count"],
        })
    for s in slot_el:
        s_n = Artifact.get_artifact_slot(s['rtype'], s['archetype'])
        artifact_slots.append({
            "name": s_n,
            "count": s["count"],
        })

    content = {
        'chart_data': {
            'artifact_slots': artifact_slots,
            'artifact_rtypes': artifact_rtypes,
            'artifact_qualities': list(artifact_qualities.values()),
            'artifact_primaries': artifact_primaries,
        },
        'filters': form_filters,
        'table': get_artifacts_table(None, filters)
    }

    return content


@celery_app.task(name='fetch.siege', bind=True)
def fetch_siege_data(self, filters):
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

    # filters here
    proper_filters = filter_siege(filters)
    sieges = sieges.filter(**proper_filters)

    # prepare filters to show in Form
    form_filters = SiegeRecord.get_filter_fields()

    ranking = sieges.values('wizard__guild__siege_ranking').annotate(
        count=Count('wizard__guild__siege_ranking'))
    siege_rankings = []
    for r in ranking:
        r_n = Guild.get_siege_ranking_name(r['wizard__guild__siege_ranking'])
        siege_rankings.append({
            "name": r_n,
            "count": r["count"]
        })

    content = {
        'chart_data': {
            'siege_rankings': siege_rankings,
        },
        'filters': form_filters,
        'table': get_siege_table(None, filters),
    }

    return content


@celery_app.task(name='fetch.cairos-detail', bind=True)
def fetch_cairos_detail_data(self, filters, cid, stage):
    dungruns = DungeonRun.objects.all().values('id', 'monsters__id', 'clear_time', 'win',
                                               ).filter(dungeon=cid, stage=stage).order_by()

    # filters here
    proper_filters = filter_cairos_detail(filters)
    dungruns = dungruns.filter(**proper_filters)

    # prepare filters to show in Form
    form_filters = DungeonRun.get_filter_fields()

    if not dungruns.exists():
        return {
            'chart_data': {
                'cairos_distribution': {},
            },
            'filters': form_filters,
            'table': [],
        }

    calc_filters = {
        'win': [],
        'ratio': [],
    }
    for key, val in filters:
        if key in ['ratio', 'win']:
            proper_val = [float(v) for v in val]
            proper_val.sort()
            calc_filters[key] = proper_val

    dungruns = list(dungruns)

    records = []
    teams = []
    for _, g in itertools.groupby(dungruns, lambda record: record['id']):
        g_t = list(g)
        record = g_t[0]
        mons = [m['monsters__id']
                for m in g_t if m['monsters__id'] is not None]
        if not mons:
            continue
        mons.sort()
        if mons not in teams:
            teams.append(mons)
            records.append({
                'team': teams[-1],
                'clear_time': [],
                'count': 0,
                'wins': 0,
                'ratio': 0,
                'points': 0,
            })
        m_id = teams.index(mons)
        if record['clear_time']:
            records[m_id]['clear_time'].append(record['clear_time'])
        records[m_id]['count'] += 1
        if record['win']:
            records[m_id]['wins'] += 1

    proper_records = []
    max_wins = 0
    fastest = min([r.total_seconds()
                   for record in records for r in record['clear_time']])
    for record in records:
        if record['wins']:
            if record['wins'] > max_wins:
                max_wins = record['wins']
            if calc_filters['win'] and (record['wins'] < calc_filters['win'][0] or record['wins'] > calc_filters['win'][1]):
                continue

            ratio = round(record['wins'] * 100 / record['count'], 2)
            if calc_filters['ratio'] and (ratio < calc_filters['ratio'][0] or ratio > calc_filters['ratio'][1]):
                continue

            proper_records.append(record)
            proper_records[-1]['team'] = MonsterImageSerializer(
                Monster.objects.filter(id__in=record['team']).only('id', 'base_monster').prefetch_related('base_monster'), many=True).data
            proper_records[-1]['ratio'] = ratio

            avg_time = sum(record['clear_time'],
                           timedelta(0)) / len(record['clear_time'])
            avg_str = str(avg_time)
            try:
                avg_index = avg_str.index('.')
                avg_str = avg_str[:avg_index]
            except ValueError:
                pass
            proper_records[-1]['clear_time'] = avg_str

            proper_records[-1]['points'] = round((min(record['wins'], 1000)**(
                1./3.) * proper_records[-1]['ratio'] / 100) / math.exp(avg_time.total_seconds() / (60 * fastest)), 4)

    form_filters['win'][1] = max_wins + 50

    content = {
        'chart_data': {
            'cairos_distribution': get_cairos_distribution(dungruns, 50),
        },
        'filters': form_filters,
        'table': proper_records,
    }

    return content


@celery_app.task(name='fetch.dimhole-detail', bind=True)
def fetch_dimhole_detail_data(self, filters, cid, stage):
    dungruns = DimensionHoleRun.objects.all().values('id', 'monsters__id', 'clear_time', 'win',
                                                     ).filter(dungeon=cid, stage=stage).order_by()

    # filters here
    proper_filters = filter_dimhole_detail(filters)
    dungruns = dungruns.filter(**proper_filters)

    # prepare filters to show in Form
    form_filters = DimensionHoleRun.get_filter_fields()

    if not dungruns.exists():
        return {
            'chart_data': {
                'dimhole_distribution': {},
            },
            'filters': form_filters,
            'table': [],
        }

    calc_filters = {
        'win': [],
        'ratio': [],
    }
    for key, val in filters:
        if key in ['ratio', 'win']:
            proper_val = [float(v) for v in val]
            proper_val.sort()
            calc_filters[key] = proper_val

    dungruns = list(dungruns)

    records = []
    teams = []
    for _, g in itertools.groupby(dungruns, lambda record: record['id']):
        g_t = list(g)
        record = g_t[0]
        mons = [m['monsters__id']
                for m in g_t if m['monsters__id'] is not None]
        if not mons:
            continue
        mons.sort()
        if mons not in teams:
            teams.append(mons)
            records.append({
                'team': teams[-1],
                'clear_time': [],
                'count': 0,
                'wins': 0,
                'ratio': 0,
                'points': 0,
            })
        m_id = teams.index(mons)
        if record['clear_time']:
            records[m_id]['clear_time'].append(record['clear_time'])
        records[m_id]['count'] += 1
        if record['win']:
            records[m_id]['wins'] += 1

    proper_records = []
    max_wins = 0
    fastest = min([r.total_seconds()
                   for record in records for r in record['clear_time']])
    for record in records:
        if record['wins']:
            if record['wins'] > max_wins:
                max_wins = record['wins']
            if calc_filters['win'] and (record['wins'] < calc_filters['win'][0] or record['wins'] > calc_filters['win'][1]):
                continue

            ratio = round(record['wins'] * 100 / record['count'], 2)
            if calc_filters['ratio'] and (ratio < calc_filters['ratio'][0] or ratio > calc_filters['ratio'][1]):
                continue

            proper_records.append(record)
            proper_records[-1]['team'] = MonsterImageSerializer(
                Monster.objects.filter(id__in=record['team']).only('id', 'base_monster').prefetch_related('base_monster'), many=True).data
            proper_records[-1]['ratio'] = ratio

            avg_time = sum(record['clear_time'],
                           timedelta(0)) / len(record['clear_time'])
            avg_str = str(avg_time)
            try:
                avg_index = avg_str.index('.')
                avg_str = avg_str[:avg_index]
            except ValueError:
                pass
            proper_records[-1]['clear_time'] = avg_str

            proper_records[-1]['points'] = round((min(record['wins'], 1000)**(
                1./3.) * proper_records[-1]['ratio'] / 100) / math.exp(avg_time.total_seconds() / (60 * fastest)), 4)

    form_filters['win'][1] = max_wins + 50

    content = {
        'chart_data': {
            'dimhole_distribution': get_cairos_distribution(dungruns, 50),
        },
        'filters': form_filters,
        'table': proper_records,
    }

    return content


@celery_app.task(name='fetch.raid-detail', bind=True)
def fetch_raid_detail_data(self, filters, stage):
    dungruns = RaidDungeonRun.objects.all().select_related(
        'monster_1',
        'monster_2',
        'monster_3',
        'monster_4',
        'monster_5',
        'monster_6',
        'monster_7',
        'monster_8',
        'leader',
        'monster_1__base_monster',
        'monster_2__base_monster',
        'monster_3__base_monster',
        'monster_4__base_monster',
        'monster_5__base_monster',
        'monster_6__base_monster',
        'monster_7__base_monster',
        'monster_8__base_monster',
        'leader__base_monster',
    ).only(
        'win', 'clear_time',
        'monster_1__id',
        'monster_2__id',
        'monster_3__id',
        'monster_4__id',
        'monster_5__id',
        'monster_6__id',
        'monster_7__id',
        'monster_8__id',
        'monster_1__base_monster__id',
        'monster_2__base_monster__id',
        'monster_3__base_monster__id',
        'monster_4__base_monster__id',
        'monster_5__base_monster__id',
        'monster_6__base_monster__id',
        'monster_7__base_monster__id',
        'monster_8__base_monster__id',
        'monster_1__base_monster__name',
        'monster_2__base_monster__name',
        'monster_3__base_monster__name',
        'monster_4__base_monster__name',
        'monster_5__base_monster__name',
        'monster_6__base_monster__name',
        'monster_7__base_monster__name',
        'monster_8__base_monster__name',
        'leader__id',
        'leader__base_monster__id',
        'leader__base_monster__name',
    ).filter(stage=stage).order_by('monster_1_id', 'monster_2_id', 'monster_3_id', 'monster_4_id', 'monster_5_id', 'monster_6_id', 'monster_7_id', 'monster_8_id', 'leader_id', )

    # filters here
    proper_filters = filter_raid_detail(filters)
    dungruns = dungruns.filter(**proper_filters)
    monsters_filter = [val for key, val in filters if key == 'monsters']
    if monsters_filter:
        mons_filter = Q()
        for m_f in monsters_filter[0]:
            m_filter = Q()
            for i in range(1, 9):
                d = {f'monster_{i}__base_monster_id': m_f}
                m_filter |= Q(**d)
            mons_filter &= m_filter
        dungruns = dungruns.filter(mons_filter)

    # prepare filters to show in Form
    form_filters = RaidDungeonRun.get_filter_fields()

    if not dungruns.exists():
        return {
            'chart_data': {
                'raid_distribution': {},
            },
            'filters': form_filters,
            'table': [],
        }

    calc_filters = {
        'win': [],
        'ratio': [],
    }
    for key, val in filters:
        if key in ['ratio', 'win']:
            proper_val = [float(v) for v in val]
            proper_val.sort()
            calc_filters[key] = proper_val

    dungruns_l = list(dungruns)

    records = []
    teams = []
    max_wins = 0
    fastest = min([record.clear_time.total_seconds()
                   for record in dungruns_l if record.clear_time])
    for team, g in itertools.groupby(dungruns_l, lambda record: (record.monster_1, record.monster_2, record.monster_3, record.monster_4, record.monster_5, record.monster_6, record.monster_7, record.monster_8, record.leader)):
        if not len([1 for m in team if m is not None]):
            continue  # empty records
        if team in teams:
            continue
        g_t = list(g)

        count = len(g_t)
        wins = len([g_.win for g_ in g_t if g_.win])
        ratio = round(wins / count * 100, 2)
        if wins > max_wins:
            max_wins = wins
        if calc_filters['win'] and (wins < calc_filters['win'][0] or wins > calc_filters['win'][1]):
            continue
        if calc_filters['ratio'] and (ratio < calc_filters['ratio'][0] or ratio > calc_filters['ratio'][1]):
            continue

        avg_time = sum([g_.clear_time for g_ in g_t if g_.win],
                       timedelta(0)) / len(g_t)
        avg_str = str(avg_time)
        try:
            avg_index = avg_str.index('.')
            avg_str = avg_str[:avg_index]
        except ValueError:
            pass

        teams.append(team)
        records.append({
            'frontline': [MonsterImageSerializer(m).data if m else None for m in team[:4]],
            'backline': [MonsterImageSerializer(m).data if m else None for m in team[4:-1]],
            'leader': MonsterImageSerializer(team[-1]).data if team[-1] else None,
            'clear_time': avg_str,
            'count': count,
            'wins': wins,
            'ratio': ratio,
            'points': round((min(wins, 1000)**(1./3.) * ratio / 100) / math.exp(avg_time.total_seconds() / (60 * fastest)), 4),
        })

    form_filters['win'][1] = max_wins + 50

    content = {
        'chart_data': {
            'raid_distribution': get_cairos_distribution(dungruns.values('win', 'clear_time'), 50),
        },
        'filters': form_filters,
        'table': records,
    }

    return content


@celery_app.task(name='fetch.rift-detail', bind=True)
def fetch_rift_detail_data(self, filters, dungeon):
    dungruns = RiftDungeonRun.objects.all().select_related(
        'monster_1',
        'monster_2',
        'monster_3',
        'monster_4',
        'monster_5',
        'monster_6',
        'monster_7',
        'monster_8',
        'leader',
        'monster_1__base_monster',
        'monster_2__base_monster',
        'monster_3__base_monster',
        'monster_4__base_monster',
        'monster_5__base_monster',
        'monster_6__base_monster',
        'monster_7__base_monster',
        'monster_8__base_monster',
        'leader__base_monster',
    ).only(
        'clear_rating', 'dmg_total',
        'monster_1__id',
        'monster_2__id',
        'monster_3__id',
        'monster_4__id',
        'monster_5__id',
        'monster_6__id',
        'monster_7__id',
        'monster_8__id',
        'monster_1__base_monster__id',
        'monster_2__base_monster__id',
        'monster_3__base_monster__id',
        'monster_4__base_monster__id',
        'monster_5__base_monster__id',
        'monster_6__base_monster__id',
        'monster_7__base_monster__id',
        'monster_8__base_monster__id',
        'monster_1__base_monster__name',
        'monster_2__base_monster__name',
        'monster_3__base_monster__name',
        'monster_4__base_monster__name',
        'monster_5__base_monster__name',
        'monster_6__base_monster__name',
        'monster_7__base_monster__name',
        'monster_8__base_monster__name',
        'leader__id',
        'leader__base_monster__id',
        'leader__base_monster__name',
    ).filter(dungeon=dungeon, clear_rating=12).order_by('monster_1_id', 'monster_2_id', 'monster_3_id', 'monster_4_id', 'monster_5_id', 'monster_6_id', 'monster_7_id', 'monster_8_id', 'leader_id', )

    # filters here
    proper_filters = filter_rift_detail(filters)
    dungruns = dungruns.filter(**proper_filters)
    monsters_filter = [val for key, val in filters if key == 'monsters']
    if monsters_filter:
        mons_filter = Q()
        for m_f in monsters_filter[0]:
            m_filter = Q()
            for i in range(1, 9):
                d = {f'monster_{i}__base_monster_id': m_f}
                m_filter |= Q(**d)
            mons_filter &= m_filter
        dungruns = dungruns.filter(mons_filter)

    # prepare filters to show in Form
    form_filters = RiftDungeonRun.get_filter_fields()

    if not dungruns.exists():
        return {
            'chart_data': {
                'rift_distribution': {},
            },
            'filters': form_filters,
            'table': [],
        }

    dungruns_l = list(dungruns)

    records = []
    teams = []
    max_dmg = max([d.dmg_total for d in dungruns if d.dmg_total])
    for team, g in itertools.groupby(dungruns_l, lambda record: (record.monster_1, record.monster_2, record.monster_3, record.monster_4, record.monster_5, record.monster_6, record.monster_7, record.monster_8, record.leader)):
        if not len([1 for m in team if m is not None]):
            continue  # empty records
        if team in teams:
            continue
        g_t = list(g)

        count = len(g_t)
        avg_dmg = round(sum([g_.dmg_total for g_ in g_t]) / count)

        teams.append(team)
        records.append({
            'frontline': [MonsterImageSerializer(m).data if m else None for m in team[:4]],
            'backline': [MonsterImageSerializer(m).data if m else None for m in team[4:-1]],
            'leader': MonsterImageSerializer(team[-1]).data if team[-1] else None,
            'count': count,
            'avg_dmg': avg_dmg,
            'points': round(math.exp(avg_dmg / -max_dmg), 4),
        })

    content = {
        'chart_data': {
            'rift_distribution': get_rift_distribution(dungruns.values_list('dmg_total', flat=True), 25),
        },
        'filters': form_filters,
        'table': records,
    }

    return content


@celery_app.task(name='generate.monster-report', bind=True)
def generate_monster_report(self, monster_id):
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
