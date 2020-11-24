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
    rune_set_names = list(RuneSet.objects.values_list('name', flat=True))

    content = {
        'rune_set': [{
            'name': name,
            'value': runes.filter(rune_set__name=name).count(),
        } for name in rune_set_names]
    }

    return content
