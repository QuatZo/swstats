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

    # temp
    rune_set_names = runes.values('rune_set__name').annotate(count=Count('rune_set__name'))

    content = {
        'rune_set': [{
            'name': rune_set['rune_set__name'],
            'count': rune_set['count'],
        } for rune_set in rune_set_names]
    }

    return content
