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
from website.functions import create_rgb_colors
from website.templatetags import get_sets

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

        hoh_date = datetime.strftime(hoh_date, "%Y-%m-%d") if type(hoh_date) == 'datetime.date' else None

        return monsters, hoh_exist, hoh_date, fusion.exists(), filename, runes

    def create_pie_plot(self, labels, values, title, colors=None):
        fig = go.Figure()
        if colors:
            fig.add_trace(go.Pie(labels=labels, values=values, marker={'colors': colors}))
        else:
            fig.add_trace(go.Pie(labels=labels, values=values))

        fig.update_layout(
            title=title,
            title_x=0.5,
            font=dict(
                family="Courier New, monospace",
                size=15,
                color="#7f7f7f"
            ),
        )

        return plotly.io.to_html(fig, include_plotlyjs=False, full_html=False)

    def create_histogram_plot(self, x, title):
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=x))

        fig.update_layout(
            title=title,
            title_x=.5,
            font=dict(
                family="Courier New, monospace",
                size=15,
                color="#7f7f7f"
            ),
            bargap=0.01,
        )

        return plotly.io.to_html(fig, include_plotlyjs=False, full_html=False)

    def create_bar_plot(self, x, y, title, colors=None, angle=90):
        fig = go.Figure()
        fig.add_trace(go.Bar(x=x, y=y, marker_color=colors))

        fig.update_layout(
            title=title,
            title_x=.5,
            font=dict(
                family="Courier New, monospace",
                size=15,
                color="#7f7f7f"
            ),
            bargap=0.05,
            xaxis=dict(
                tickangle=angle,
            )
        )
        return plotly.io.to_html(fig, include_plotlyjs=False, full_html=False)

    def generate_plots(self, monsters, monsters_runes, base_monster):
        plots = list()

        #################################################
        # PREPARE DATA
        df = pd.DataFrame.from_records(monsters.values(), index="id")
        for result in monsters_runes:
            for i, rune in enumerate(result['runes']):
                if rune is not None:
                    df.loc[result['monster'].id, "rune #" + str(i + 1)] = Rune().get_substat_display(rune.primary)
                else:
                    df.loc[result['monster'].id, "rune #" + str(i + 1)] = rune
            set_names = [str(set_name) for set_name in get_sets.get_sets(result['runes'])]
            set_names.sort()
            df.loc[result['monster'].id, 'sets'] = ' + '.join(set_names)
        #################################################

        #################################################
        # STARS DISTRIBUTION
        stars = df["stars"].value_counts()
        plots.append(self.create_pie_plot(stars.index, stars, "Stars"))
        #################################################


        #################################################
        # EQUIPPED RUNES DISTRIBUTION
        # PICK ONLY 6* with runes with runes
        df = df[df['stars'] == 6]
        if not df.shape[0]: # no 6* builds
            return plots

        df_full = df.copy()
        runes_cols = ["rune #" + str(i) for i in range(1 ,7)]
        df.dropna(subset=runes_cols, how='any', inplace=True) # delete without runes
        plots.append(self.create_pie_plot(["With Runes", "Without Runes"], [df.shape[0], df_full.shape[0] - df.shape[0]], "Runes <br>(only 6*)", ['#77ff77', '#ff7777']))
        #################################################

        if not df.shape[0]: # no builds with runes
            return plots

        #################################################
        # SKILL-UPS DISTRIBUTION
        max_skills = str(base_monster.max_skills)
        df['skills'] = df['skills'].astype('str')
        full_skillups_indexes = df['skills'][df['skills'] == max_skills].index
        df.loc[full_skillups_indexes, 'skills'] = "Yes"
        df.loc[~df.index.isin(full_skillups_indexes), 'skills'] = "No"

        skillups = df["skills"].value_counts().sort_index()
        plots.append(self.create_pie_plot(skillups.index, skillups, "Skill-ups <br>(only 6* with equipped runes)", ['#ff7777', '#77ff77']))
        #################################################
        
        #################################################
        # TRANSMOG
        full_stransmog_indexes = df['transmog'][df['transmog'] == True].index
        df.loc[full_stransmog_indexes, 'transmog'] = "Yes"
        df.loc[~df.index.isin(full_stransmog_indexes), 'transmog'] = "No"

        transmogs = df["transmog"].value_counts().sort_index()
        plots.append(self.create_pie_plot(transmogs.index, transmogs, "Transmogrifications <br>(only 6* with equipped runes)", ['#ff7777', '#77ff77']))
        #################################################

        #################################################
        # EFFECTIVE HP & EFFECTIVE HP WHILE DEF BROKEN
        plots.append(self.create_histogram_plot(df['eff_hp'], "Effective HP Distribution<br>(only 6* with equipped runes)"))
        plots.append(self.create_histogram_plot(df['eff_hp_def_break'], "Effective HP with Defense Break<br>(only 6* with equipped runes)"))
        #################################################

        #################################################
        # HP & DEFENSE DISTRIBUTION
        plots.append(self.create_histogram_plot(df['hp'], "HP Distribution<br>(only 6* with equipped runes)"))
        plots.append(self.create_histogram_plot(df['defense'], "Defense Distribution<br>(only 6* with equipped runes)"))
        #################################################
        
        #################################################
        # ATTACK & SPEED DISTRIBUTION
        plots.append(self.create_histogram_plot(df['attack'], "Attack Distribution<br>(only 6* with equipped runes)"))
        plots.append(self.create_histogram_plot(df['speed'], "Speed Distribution<br>(only 6* with equipped runes)"))
        #################################################

        #################################################
        # CRIT RATE & CRIT DMG DISTRIBUTION
        plots.append(self.create_histogram_plot(df['crit_rate'], "Critical Rate Distribution<br>(only 6* with equipped runes)"))
        plots.append(self.create_histogram_plot(df['crit_dmg'], "Critical Damage Distribution<br>(only 6* with equipped runes)"))
        #################################################
        
        #################################################
        # AVERAGE RUNE EFFICIENCY & CRIT DMG DISTRIBUTION
        plots.append(self.create_histogram_plot(df['avg_eff'], "Average Rune Efficiency Distribution<br>(only 6* with equipped runes)"))
        #################################################

        #################################################
        # SETS BAR
        counts = df["sets"].value_counts()
        counts = counts[(counts > 1) & (counts > round(counts[0] / 50))]
        colors = create_rgb_colors(counts.shape[0], True)
        plots.append(self.create_bar_plot(counts.index, counts, "Sets Distribution <br>(only 6* with equipped runes)", colors))
        #################################################

        #################################################
        # 4 SETS BAR
        sets_4 = ['Violent', 'Swift', 'Rage', 'Fatal', 'Despair', 'Vampire']
        set_sum = dict()
        for set_4 in sets_4:
            indexes = [val for val in counts.index if set_4 in val]
            set_count = counts.loc[indexes]
            if set_count.sum():
                set_sum[set_4] = set_count.sum()
        set_sum = {k: v for k, v in sorted(set_sum.items(), key=lambda item: item[1], reverse=True)}
        sets_4_x, sets_4_y = list(set_sum.keys()), list(set_sum.values())
        colors = create_rgb_colors(len(sets_4_x), True)
        plots.append(self.create_bar_plot(sets_4_x,  sets_4_y, "4-Sets Distribution <br>(only 6* with equipped runes)", colors))
        #################################################

        #################################################
        # MOST COMMON BUILDS
        builds_count = df.groupby(["rune #2", "rune #4", "rune #6"]).size().reset_index(name='count').sort_values('count', ascending=False).reset_index(drop=True)
        builds_count = builds_count[(builds_count['count'] > 1) & (builds_count['count'] > round(builds_count['count'][0] / 50))].sort_values(["count"], ascending=False) # single builds to drop
        builds_count['build'] = builds_count['rune #2'] + ' / ' + builds_count['rune #4'] + ' / ' + builds_count['rune #6']
        colors = create_rgb_colors(builds_count.shape[0], True)
        plots.append(self.create_bar_plot(builds_count['build'],  builds_count['count'], "Most Common Builds <br>(only 6* with equipped runes)", colors, 30))
        #################################################

        #################################################
        # SLOT 2, 4 & 6
        counts_slot2 = df["rune #2"].value_counts()
        counts_slot2 = counts_slot2[counts_slot2 > 1]
        counts_slot4 = df["rune #4"].value_counts()
        counts_slot4 = counts_slot4[counts_slot4 > 1]
        counts_slot6 = df["rune #6"].value_counts()
        counts_slot6 = counts_slot6[counts_slot6 > 1]

        colors = create_rgb_colors(counts_slot2.shape[0], True)
        plots.append(self.create_bar_plot(counts_slot2.index, counts_slot2.values, "Most Common Slot 2<br>(only 6* with equipped runes)", colors, 30))
        colors = create_rgb_colors(counts_slot4.shape[0], True)
        plots.append(self.create_bar_plot(counts_slot4.index, counts_slot4.values, "Most Common Slot 4<br>(only 6* with equipped runes)", colors, 30))
        colors = create_rgb_colors(counts_slot6.shape[0], True)
        plots.append(self.create_bar_plot(counts_slot6.index, counts_slot6.values, "Most Common Slot 6<br>(only 6* with equipped runes)", colors, 30))
        #################################################

        return plots

    def create(self, request):
        # upload by using ajax, focused on stuff that Desktop App had
        context = { }

        if request.is_ajax():
            data = request.data
            base_monster = MonsterBase.objects.get(id=data)
            
            monsters, hoh_exist, hoh_date, fusion_exist, filename, monsters_runes = self.get_monster_info(base_monster)

            plots = self.generate_plots(monsters, monsters_runes, base_monster)

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

def get_report_menu(request):
    return render( request, 'website/report/report_menu.html')

def get_report(request):
    """Return the Report page."""
    monsters_base = MonsterBase.objects.filter(~Q(archetype=5) & ~Q(awaken=0)).prefetch_related('monster_set') # archetype=5 -> Material Monsters, awaken=0 -> Unawakened

    base = list()
    for monster_base in monsters_base:
        if monster_base.monster_set.count():
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