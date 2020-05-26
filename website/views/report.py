from django.http import HttpResponse
from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from django.template.loader import render_to_string
from django.conf import settings
from django.db.models import Count, Q, Avg

import logging
import time
import os
from operator import itemgetter
from datetime import datetime

import pandas as pd
import numpy as np
import plotly
import plotly.graph_objects as go

from website.models import *
from website.serializers import CommandSerializer

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


    def generate_plots(self, monsters, monsters_runes):
        plots = list()

        df = pd.DataFrame.from_records(monsters.values(), index="id")
        for result in monsters_runes:
            for i, rune in enumerate(result['runes']):
                df.loc[result['monster'].id, "rune #" + str(i + 1)] = rune

        stars = df["stars"].value_counts()

        fig = go.Figure()
        fig.add_trace(go.Pie(labels=stars.index, values=stars))

        fig.update_layout(
            title=f"Stars Distribution",
            font=dict(
                family="Courier New, monospace",
                size=15,
                color="#7f7f7f"
            ),
        )

        plots.append(plotly.io.to_html(fig, include_plotlyjs=False, full_html=False))

        return plots

    def create(self, request):
        # upload by using ajax, focused on stuff that Desktop App had
        context = { }

        if request.is_ajax():
            data = request.data
            base_monster = MonsterBase.objects.get(id=data)
            
            monsters, hoh_exist, hoh_date, fusion_exist, filename, monsters_runes = self.get_monster_info(base_monster)

            plots = self.generate_plots(monsters, monsters_runes)

            context = {
                'base_monster': base_monster,
                'monsters': monsters,
                'monsters_runes': monsters_runes,
                'hoh': hoh_exist,
                'hoh_date': hoh_date,
                'fusion': fusion_exist,
                'filename': filename,
                'plots': plots,
            }

            html = render_to_string('website/report/report_generate.html', context)
            return HttpResponse(html)

def get_report(request):
    """Return the Report page."""
    monsters_base = MonsterBase.objects.filter(~Q(archetype=5) & ~Q(awaken=0)).prefetch_related('monster_set') # archetype=5 -> Material Monsters, awaken=0 -> Unawakened

    base = list()
    for monster_base in monsters_base:
        base.append({
            'id': monster_base.id,
            'name': monster_base.name,
            'count': monster_base.monster_set.count(),
        })

    base = sorted(base, key=itemgetter('count'), reverse = True)

    context = {
        'base': base,
    }

    return render( request, 'website/report/report_index.html', context)

def get_old_reports(request):
    images = dict()

    app_static_dir = os.path.join(settings.BASE_DIR, 'website', 'static', 'website', 'reports')

    for filename in os.listdir(app_static_dir):
        if filename.endswith(".png"):
            images[filename] = os.path.getmtime(app_static_dir + '/' + filename)

    images = {k: v for k, v in sorted(images.items(), key=lambda image: image[1], reverse=True)} # reverse=True -> descending
    for key, val in images.items():
        images[key] = datetime.strftime(datetime.fromtimestamp(val), "%Y-%m-%d")

    context = {
        'images': images, 
    }

    return render( request, 'website/report/report_old.html', context)