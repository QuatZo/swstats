from django.db.models import Count, Q, F, Avg

from website.celery import app as celery_app
from website.tasks import handle_profile_upload_task
from website.models import Rune, RuneSet, Monster, MonsterBase
from .functions import get_scoring_for_profile, get_profile_comparison_with_database, filter_runes, get_runes_table, filter_monsters, get_monsters_table


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
