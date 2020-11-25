from django.db.models import Count, Q, F, Avg

from website.celery import app as celery_app
from website.tasks import handle_profile_upload_task
from website.models import Rune, RuneSet
from .functions import get_scoring_for_profile, get_profile_comparison_with_database


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


@celery_app.task(name='runes.fetch', bind=True)
def fetch_runes_data(self, filters):
    runes = Rune.objects.all().select_related('rune_set', ).defer(
        'wizard', 'base_value', 'sell_value').order_by()
    # filters here
    # runes.filter(**filters)

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
    }

    return content
