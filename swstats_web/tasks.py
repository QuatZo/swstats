from django.db.models import Count, Q, F, Avg

from website.celery import app as celery_app
from website.tasks import handle_profile_upload_task
from website.models import Rune, RuneSet, Monster, MonsterBase, Artifact, SiegeRecord, Guild, DungeonRun, DimensionHoleRun
from .functions import *
from .serializers import MonsterImageSerializer

import itertools
import operator
from datetime import timedelta
import math


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
    monsters = Monster.objects.all().select_related('base_monster', 'base_monster__family', ).prefetch_related(
        'runes', 'runes_rta', 'artifacts', 'artifacts_rta', 'runes__rune_set', 'runes_rta__rune_set',).defer('wizard', 'source', 'transmog', ).order_by()

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

    content = {
        'chart_data': {
            'monster_elements': list(monster_elements.values()),
            'monster_archetypes': list(monster_archetypes.values()),
            'monster_awakens': list(monster_awakens.values()),
            'monster_stars': list(monster_stars.values()),
        },
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
