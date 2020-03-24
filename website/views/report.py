from django.http import HttpResponse
from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from django.template.loader import render_to_string

import logging
import time

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
    context = {
        'base_monsters': MonsterBase.objects.all(), 
    }
    return render( request, 'website/report/report_index.html', context)