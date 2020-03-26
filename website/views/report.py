from django.http import HttpResponse
from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from django.template.loader import render_to_string
from django.conf import settings
from django.db.models import Count


import logging
import time
import os
from operator import itemgetter

from website.models import *
from website.serializers import CommandSerializer
from website.exceptions import ProfileDoesNotExist

# Create your views here.
class ReportGeneratorViewSet(viewsets.ViewSet):
    def get_monster_info(self, base_monster):
        monsters = Monster.objects.filter(base_monster=base_monster).prefetch_related('runes')
        runes = list()
        for monster in monsters:
            monster_runes = [ None, None, None, None, None, None ]
            for rune in monster.runes.all():
                monster_runes[rune.slot - 1] = rune
            runes.append({'monster': monster, 'runes': monster_runes})

        monster_name = base_monster.name.lower().replace(' (', '_').replace(')', '').replace(' ', '')
        filename = monster_name + '_' + time.strftime("%Y%m%d") + '.csv'
        
        if base_monster.awaken:
            monster_id = int(base_monster.id / 100) * 100 + base_monster.id % 10
            hoh = MonsterHoh.objects.filter(monster__id=monster_id)
            hoh_date = None
            hoh_exist = False
            if hoh.exists():
                hoh_exist = True
                hoh_date = hoh.first().date_open

            fusion = MonsterFusion.objects.filter(monster=monster_id)
        else:
            hoh = MonsterHoh.objects.filter(monster=base_monster)
            hoh_date = None
            hoh_exist = False
            if hoh.exists():
                hoh_exist = True
                hoh_date = hoh.first().date_open

            fusion = MonsterFusion.objects.filter(monster=base_monster)

        return monsters, hoh_exist, hoh_date, fusion.exists(), filename, runes

    def create(self, request):
        # upload by using ajax, focused on stuff that Desktop App had
        context = { }

        if request.is_ajax():
            data = request.data
            base_monster = MonsterBase.objects.get(id=data)
            
            monsters, hoh_exist, hoh_date, fusion_exist, filename, monsters_runes = self.get_monster_info(base_monster)

            context = {
                'base_monster': base_monster,
                'monsters': monsters,
                'monsters_runes': monsters_runes,
                'hoh': hoh_exist,
                'hoh_date': hoh_date,
                'fusion': fusion_exist,
                'filename': filename,
            }
            html = render_to_string('website/report/report_generate.html', context)
            return HttpResponse(html)

def get_report(request):
    """Return the Report page."""
    counts = list(Monster.objects.all().values('base_monster__name').annotate(total=Count('base_monster__name')))
    
    counts = sorted(counts, key=itemgetter('total'), reverse = True)
    counts = [record for record in counts if record['total'] > 100]
    base_monsters = [record['base_monster__name'] for record in counts]

    monsters_runes = Monster.objects.filter(base_monster__name__in=base_monsters).prefetch_related('runes', 'base_monster')

    for record in counts:
        for monster_runes in monsters_runes:
            if monster_runes.base_monster.name == record['base_monster__name']: # base monster name
                if 'equipped' not in record.keys():
                    record['equipped'] = 0
                runes_amount = monster_runes.runes.all().count()
                if runes_amount == 6:
                    record['equipped'] += 1
        if record['equipped'] > record['total']:
            record['equipped'] = record['total']

    context = {
        'base_monsters': MonsterBase.objects.all(), 
        'counts': counts,
    }
    return render( request, 'website/report/report_index.html', context)

def get_old_reports(request):
    image_list = list()

    app_static_dir = os.path.join(settings.BASE_DIR, 'website', 'static', 'website', 'reports')

    for filename in os.listdir(app_static_dir):
        if filename.endswith(".png"):
            image_list.append(filename)

    context = {
        'images': image_list, 
    }

    return render( request, 'website/report/report_old.html', context)