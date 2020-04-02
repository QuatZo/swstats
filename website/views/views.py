from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.db.models import F, Q, Avg, Min, Max, Sum, Count, FloatField
from django.template.loader import render_to_string

from website.models import *
from website.tasks import *

import matplotlib.cm as cm
import numpy as np

def get_runes(request):
    task = get_runes_task.delay(dict(request.GET))

    return render( request, 'website/runes/rune_index.html', {'task_id': task.id})

def get_runes_ajax(request, task_id):
    if request.is_ajax():
        data = get_siege_records_task.AsyncResult(task_id) 

        if data.ready():
            context = data.get()

            context['best_runes'] = Rune.objects.filter(id__in=context['best_runes_ids']).prefetch_related('rune_set', 'equipped_runes', 'equipped_runes__base_monster').order_by('-efficiency')
            context['fastest_runes'] = Rune.objects.filter(id__in=context['fastest_runes_ids']).prefetch_related('rune_set', 'equipped_runes', 'equipped_runes__base_monster').order_by('-sub_speed')

            html = render_to_string('website/runes/rune_index_ajax.html', context) # return JSON/Dict like during Desktop Upload
            return HttpResponse(html)

    return HttpResponse('')

def get_siege_records(request):
    task = get_siege_records_task.delay(dict(request.GET))

    return render( request, 'website/siege/siege_index.html', {'task_id': task.id})

def get_siege_records_ajax(request, task_id):
    if request.is_ajax():
        data = get_siege_records_task.AsyncResult(task_id) 

        if data.ready():
            context = data.get()
            context['best_records'] = SiegeRecord.objects.filter(id__in=context['records_ids']).prefetch_related('monsters', 'monsters__base_monster', 'wizard', 'wizard__guild', 'leader', 'leader__base_monster', 'monsters__base_monster__family').annotate(sorting_val=Sum((F('win') + 250) * F('ratio'), output_field=FloatField())).order_by('-sorting_val')[:context['best_amount']]

            html = render_to_string('website/siege/siege_index_ajax.html', context) # return JSON/Dict like during Desktop Upload
            return HttpResponse(html)

    return HttpResponse('')
