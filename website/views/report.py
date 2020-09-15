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
from itertools import chain

import pandas as pd
import numpy as np
import plotly
import plotly.graph_objects as go

from website.models import *
from website.serializers import CommandSerializer
from website.functions import create_rgb_colors
from website.templatetags.runes import get_sets

# HELPFUL FUNCTIONS
def get_monster_info(base_monster):
    monsters = Monster.objects.filter(
        base_monster=base_monster).prefetch_related('runes', 'runes__rune_set', 'artifacts', )
    runes = dict()
    artifacts = dict()
    for monster in monsters:
        monster_runes = [None, None, None, None, None, None]
        monster_artifacts = [None, None]
        for rune in monster.runes.all():
            monster_runes[rune.slot - 1] = rune
        runes[monster.id] = monster_runes

        for artifact in monster.artifacts.all():
            monster_artifacts[artifact.rtype - 1] = artifact
        artifacts[monster.id] = monster_artifacts

    monster_name = base_monster.name.lower().replace(
        ' (', '_').replace(')', '').replace(' ', '')
    filename = monster_name + '_' + time.strftime("%Y%m%d") + '.csv'

    if base_monster.awaken:
        monster_id = int(base_monster.id / 100) * 100 + base_monster.id % 10
        hoh = MonsterHoh.objects.filter(monster__id=monster_id)
        hoh_date = None
        hoh_exist = False
        if hoh.exists():
            hoh_exist = True
            hoh_date = datetime.strftime(hoh.first().date_open, "%Y-%m-%d")

        fusion = MonsterFusion.objects.filter(monster=monster_id)
    else:
        hoh = MonsterHoh.objects.filter(monster=base_monster)
        hoh_date = None
        hoh_exist = False
        if hoh.exists():
            hoh_exist = True
            hoh_date = datetime.strftime(hoh.first().date_open, "%Y-%m-%d")

        fusion = MonsterFusion.objects.filter(monster=base_monster)

    family = MonsterBase.objects.filter(
        family=base_monster.family).order_by('attribute', 'id')


    return monsters, hoh_exist, hoh_date, fusion.exists(), filename, runes, family, artifacts

def create_pie_plot(labels, values, title, colors=None, bot=False):
    fig = go.Figure()
    if colors:
        fig.add_trace(go.Pie(labels=labels, values=values,
                             marker={'colors': colors}))
    else:
        fig.add_trace(go.Pie(labels=labels, values=values))

    template = 'plotly_dark'
    if bot:
        template = 'plotly'

    fig.update_layout(
        title=title,
        title_x=0.5,
        font=dict(
            family="Courier New, monospace",
            size=15,
            color="#7f7f7f",
        ),
        template=template,
    )

    return plotly.io.to_html(fig, include_plotlyjs=False, full_html=False)

def create_histogram_plot(x, title, bot=False):
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=x))

    template = 'plotly_dark'
    if bot:
        template = 'plotly'

    fig.update_layout(
        title=title,
        title_x=.5,
        font=dict(
            family="Courier New, monospace",
            size=15,
            color="#7f7f7f"
        ),
        bargap=0.01,
        template=template,
    )

    return plotly.io.to_html(fig, include_plotlyjs=False, full_html=False)

def create_bar_plot(x, y, title, colors=None, angle=90, bot=False):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=y, marker_color=colors))

    if type(x) is not list:
        max_len = x.map(len).max()
    elif len(x):
        max_len = max([len(el) for el in x])
    else:
        max_len = 0

    template = 'plotly_dark'
    if bot:
        template = 'plotly'

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
            tickmode='linear',
        ),
        template=template,
    )

    if max_len > 10:
        fig.update_layout(
            margin=dict(
                l=10,
                r=10,
                b=max_len * 9.5,
            ),
        )

    return plotly.io.to_html(fig, include_plotlyjs=False, full_html=False)

def create_horizontal_bar_plot(x, y, title, colors=None, bot=False):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=y, marker_color=colors, orientation='h'))

    template = 'plotly_dark'
    if bot:
        template = 'plotly'

    fig.update_layout(
        title=title,
        title_x=.5,
        font=dict(
            family="Courier New, monospace",
            size=15,
            color="#7f7f7f"
        ),
        bargap=0.05,
        template=template,
    )

    return plotly.io.to_html(fig, include_plotlyjs=False, full_html=False)

def generate_plots(monsters, monsters_runes, base_monster, monsters_artifacts, bot=False):
    plots = list()
    no_records = 'No information given'
    top_sets = list()

    #################################################
    # PREPARE DATA
    df = pd.DataFrame.from_records(monsters.values(), index="id")
    for mon_id, result in monsters_runes.items():
        for i, rune in enumerate(result):
            if rune is not None:
                df.loc[mon_id, "rune #" +
                       str(i + 1)] = Rune().get_substat_display(rune.primary)
            else:
                df.loc[mon_id, "rune #" + str(i + 1)] = rune

        set_names, broken = get_sets(result, True)
        set_names = [str(set_name) for set_name in set_names]
        set_names.sort()

        if broken:
            set_names.append('Broken')

        df.loc[mon_id, 'sets'] = ' + '.join(set_names)

    df["artifact element"] = np.nan
    df["artifact element substats"] = np.nan
    df["artifact type"] = np.nan
    df["artifact type substats"] = np.nan
    df = df.astype({'artifact element substats': 'object', 'artifact type substats': 'object',})

    for mon_id, result in monsters_artifacts.items():
        for i, artifact in enumerate(result):
            if artifact is not None:
                r_type = 'element' if artifact.rtype == 1 else 'type'
                df.loc[mon_id, f"artifact {r_type}"] = artifact.get_primary_display()
                df.at[mon_id, f"artifact {r_type} substats"] = artifact.substats
            else:
                r_type = 'element' if i == 0 else 'type'
                df.loc[mon_id, f"artifact {r_type}"] = artifact
                df.loc[mon_id, f"artifact {r_type} substats"] = artifact
    #################################################

    #################################################
    # STARS DISTRIBUTION
    stars = df["stars"].value_counts()
    stars_plot = create_pie_plot(stars.index, stars, "Stars", None, bot)
    #################################################

    #################################################
    # EQUIPPED RUNES DISTRIBUTION
    # PICK ONLY 6* with runes with runes
    df = df[df['stars'] == 6]
    if not df.shape[0]:  # no 6* builds
        return plots, no_records, None, None, top_sets, None, None, None

    df_full = df.copy()
    runes_cols = ["rune #" + str(i) for i in range(1, 7)]
    df.dropna(subset=runes_cols, how='any',
              inplace=True)  # delete without runes
    equipped_runes_plot = create_pie_plot(["With<br>Runes", "Without<br>Runes"], [
                                          df.shape[0], df_full.shape[0] - df.shape[0]], "Runes <br>(only 6*)", ['#77ff77', '#ff7777'], bot)
    #################################################

    if not df.shape[0]:  # no builds with runes
        return plots, no_records, None, None, top_sets, None, None, None

    #################################################
    # SKILL-UPS DISTRIBUTION
    max_skills = str(base_monster.max_skills)
    df['skills'] = df['skills'].astype('str')
    full_skillups_indexes = df['skills'][df['skills'] == max_skills].index
    df.loc[full_skillups_indexes, 'skills'] = "Yes"
    df.loc[~df.index.isin(full_skillups_indexes), 'skills'] = "No"

    skillups = df["skills"].value_counts().sort_index()
    skillups_plot = create_pie_plot(
        skillups.index, skillups, "Fully skilled up <br>(only 6* with equipped runes)", ['#ff7777', '#77ff77'], bot)
    #################################################

    #################################################
    # TRANSMOG
    full_stransmog_indexes = df['transmog'][df['transmog'] == True].index
    df.loc[full_stransmog_indexes, 'transmog'] = "Yes"
    df.loc[~df.index.isin(full_stransmog_indexes), 'transmog'] = "No"

    transmogs = df["transmog"].value_counts().sort_index()
    transmogs_plot = create_pie_plot(
        transmogs.index, transmogs, "Transmogrifications <br>(only 6* with equipped runes)", ['#ff7777', '#77ff77'], bot)
    #################################################

    #################################################
    # EFFECTIVE HP & EFFECTIVE HP WHILE DEF BROKEN
    eff_hp_plot = create_histogram_plot(
        df['eff_hp'], "Effective HP Distribution<br>(only 6* with equipped runes)", bot)
    eff_hp_def_plot = create_histogram_plot(
        df['eff_hp_def_break'], "Effective HP with Defense Break<br>(only 6* with equipped runes)", bot)
    #################################################

    #################################################
    # SPEED & HP & ATTACK & DEFENSE & CRIT RATE & CRIT DMG DISTRIBUTION
    plots.append(create_histogram_plot(
        df['speed'], "Speed Distribution<br>(only 6* with equipped runes)", bot))
    plots.append(create_histogram_plot(
        df['hp'], "HP Distribution<br>(only 6* with equipped runes)", bot))
    plots.append(create_histogram_plot(
        df['attack'], "Attack Distribution<br>(only 6* with equipped runes)", bot))
    plots.append(create_histogram_plot(
        df['defense'], "Defense Distribution<br>(only 6* with equipped runes)", bot))
    plots.append(create_histogram_plot(
        df['crit_rate'], "Critical Rate Distribution<br>(only 6* with equipped runes)", bot))
    plots.append(create_histogram_plot(
        df['crit_dmg'], "Critical Damage Distribution<br>(only 6* with equipped runes)", bot))
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
    plots.append(create_bar_plot(counts_slot2.index, counts_slot2.values,
                                 "Most Common Slot 2<br>(only 6* with equipped runes)", colors, 30, bot))
    colors = create_rgb_colors(counts_slot4.shape[0], True)
    plots.append(create_bar_plot(counts_slot4.index, counts_slot4.values,
                                 "Most Common Slot 4<br>(only 6* with equipped runes)", colors, 30, bot))
    colors = create_rgb_colors(counts_slot6.shape[0], True)
    plots.append(create_bar_plot(counts_slot6.index, counts_slot6.values,
                                 "Most Common Slot 6<br>(only 6* with equipped runes)", colors, 30, bot))
    #################################################

    #################################################
    # SETS BAR
    counts = df["sets"].value_counts()
    counts = counts[counts > round(counts[0] / 50)]
    if len(counts) > 20:
        counts = counts[:20]
    colors = create_rgb_colors(counts.shape[0], True)

    top_sets_temp = counts[:min(len(counts), 3)]
    top_sets_temp = [top_set.replace(' + ', ' / ') + ' (' + str(round(100 * top_count / len(
        df))) + '%)' for top_set, top_count in top_sets_temp.to_dict().items()]
    for i in range(len(top_sets_temp)):
        top_sets.append({
            'id': i+1,
            'sets': top_sets_temp[i],
            'message': f'{base_monster.name} top {i + 1} set: {top_sets_temp[i]}',
        })

    if len(top_sets) < 3:
        for i in range(3 - len(top_sets)):
            top_sets.append({
                'id': i + len(top_sets) + 1,
                'sets': '',
                'message': '',
            })

    plot_sets = create_bar_plot(
        counts.index, counts, "Sets Distribution <br>(only 6* with equipped runes)", colors, 90, bot)

    if not bot:
        plots.append(plot_sets)
    #################################################

    #################################################
    # 4 SETS BAR
    sets_4 = ['Violent', 'Swift', 'Rage', 'Fatal', 'Despair', 'Vampire']
    counts = df["sets"].value_counts()
    counts = counts[counts > round(counts[0] / 50)]
    set_sum = dict()
    for set_4 in sets_4:
        indexes = [val for val in counts.index if set_4 in val]
        set_count = counts.loc[indexes]
        if set_count.sum():
            set_sum[set_4] = set_count.sum()
    set_sum = {k: v for k, v in sorted(
        set_sum.items(), key=lambda item: item[1], reverse=True)}
    sets_4_x, sets_4_y = list(set_sum.keys()), list(set_sum.values())
    colors = create_rgb_colors(len(sets_4_x), True)
    plots.append(create_bar_plot(sets_4_x,  sets_4_y,
                                 "4-Sets Distribution <br>(only 6* with equipped runes)", colors, 90, bot))
    #################################################

    #################################################
    # AVERAGE RUNE EFFICIENCY & DISTRIBUTION
    plots.append(create_histogram_plot(
        df['avg_eff'], "Average Rune Efficiency Distribution<br>(only 6* with equipped runes)", bot))
    #################################################

    #################################################
    # MOST COMMON BUILDS
    builds_count = df.groupby(["rune #2", "rune #4", "rune #6"]).size().reset_index(
        name='count').sort_values(["count"], ascending=False)

    builds_count_proper = dict()
    for row in builds_count.values.tolist():
        set_temp = row[:3]
        set_temp.sort()
        set_temp_txt = '/'.join(set_temp)
        if set_temp_txt not in builds_count_proper:
            builds_count_proper[set_temp_txt] = {
                'build': '/'.join(row[:3]),
                'count': 0,
            }
        builds_count_proper[set_temp_txt]['count'] += row[3]

    builds_count_final = list()
    for b in builds_count_proper.values():
        if b['count'] < 5:
            continue
        builds_count_final.append(b)

    builds_count = sorted(builds_count_final,
                          key=lambda k: k['count'], reverse=True)
    builds_count = {k: [dic[k] for dic in builds_count]
                    for k in builds_count[0]} if builds_count else {'build': [], 'count': []}
    colors = create_rgb_colors(len(builds_count['build']), True)

    plot_builds = create_bar_plot(builds_count['build'],  builds_count['count'],
                                  "Most Common Builds <br>(only 6* with equipped runes)", colors, 30, bot)
    if not bot:
        plots.append(plot_builds)

    if len(builds_count['build']):
        most_common_build = builds_count['build'][0]
    else:
        most_common_build = no_records
    #################################################

    #################################################
    # ARTIFACTS
    plot_artifacts_element_main = None
    plot_artifacts_archetype_main = None
    artifact_best = { 'element': None, 'archetype': None, }
    df_artifacts_element_main = df['artifact element'].copy().value_counts()
    df_artifacts_element_substats = df['artifact element substats'].copy().dropna()
    df_artifacts_element_substats = pd.Series(list(chain.from_iterable(df_artifacts_element_substats))).value_counts()
    if df_artifacts_element_substats.shape[0]:
        artifact_best['element'] = Artifact().get_artifact_substat(df_artifacts_element_substats.index[0])
        df_artifacts_element_substats = df_artifacts_element_substats[df_artifacts_element_substats > 5]
        df_artifacts_element_substats = pd.DataFrame(df_artifacts_element_substats, columns=['count']).reset_index()
        df_artifacts_element_substats['index'] = df_artifacts_element_substats['index'].apply(Artifact().get_artifact_substat)
        df_artifacts_element_substats = df_artifacts_element_substats.to_dict(orient='list')
        
        colors = create_rgb_colors(len(df_artifacts_element_substats['index']), True)
        plot_artifacts_element_main = create_pie_plot(df_artifacts_element_main.index, df_artifacts_element_main, "Artifact Element Main Stat", None, bot)
        if not bot:
            plots.append(plot_artifacts_element_main)
        plots.append(create_horizontal_bar_plot(df_artifacts_element_substats['count'], df_artifacts_element_substats['index'], "Artifact Element Substat Distribution<br>(only 6* with equipped runes)", colors, bot))

    df_artifacts_archetype_main = df['artifact type'].copy().value_counts()
    df_artifacts_archetype_substats = df['artifact type substats'].copy().dropna()
    df_artifacts_archetype_substats = pd.Series(list(chain.from_iterable(df_artifacts_archetype_substats))).value_counts()
    if df_artifacts_archetype_substats.shape[0]:
        artifact_best['archetype'] = Artifact().get_artifact_substat(df_artifacts_archetype_substats.index[0])
        df_artifacts_archetype_substats = df_artifacts_archetype_substats[df_artifacts_archetype_substats > 5]
        df_artifacts_archetype_substats = pd.DataFrame(df_artifacts_archetype_substats, columns=['count']).reset_index()
        df_artifacts_archetype_substats['index'] = df_artifacts_archetype_substats['index'].apply(Artifact().get_artifact_substat)
        df_artifacts_archetype_substats = df_artifacts_archetype_substats.to_dict(orient='list')

        colors = create_rgb_colors(len(df_artifacts_archetype_substats['index']), True)
        plot_artifacts_archetype_main = create_pie_plot(df_artifacts_archetype_main.index, df_artifacts_archetype_main, "Artifact Archetype Main Stat", None, bot)
        if not bot:
            plots.append(plot_artifacts_archetype_main)
        plots.append(create_horizontal_bar_plot(df_artifacts_archetype_substats['count'], df_artifacts_archetype_substats['index'], "Artifact Archetype Substat Distribution<br>(only 6* with equipped runes)", colors, bot))
    #################################################

    plots.append(eff_hp_plot)
    plots.append(eff_hp_def_plot)
    plots.append(stars_plot)
    plots.append(equipped_runes_plot)
    plots.append(skillups_plot)
    plots.append(transmogs_plot)

    return plots, most_common_build, plot_sets, plot_builds, top_sets, plot_artifacts_element_main, plot_artifacts_archetype_main, artifact_best


class ReportGeneratorViewSet(viewsets.ViewSet):
    def create(self, request):
        # upload by using ajax, focused on stuff that Desktop App had
        context = {}

        if request.is_ajax():
            data = request.data
            base_monster = MonsterBase.objects.get(id=data)

            monsters, hoh_exist, hoh_date, fusion_exist, filename, monsters_runes, _, monsters_artifacts = get_monster_info(
                base_monster)

            plots, _, _, _, _, _, _, _ = generate_plots(
                monsters, monsters_runes, base_monster, monsters_artifacts)

            context = {
                'base_monster': base_monster,
                'monsters': monsters,
                'monsters_runes': monsters_runes,
                'monsters_artifacts': monsters_artifacts,
                'hoh': hoh_exist,
                'hoh_date': hoh_date,
                'fusion': fusion_exist,
                'filename': filename,
                'plots': plots,
            }

            html = render_to_string(
                'website/report/report_generate.html', context)

            return HttpResponse(html)


def get_report_menu(request):
    return render(request, 'website/report/report_menu.html')


def get_report(request):
    """Return the Report page."""
    monsters_base = list(MonsterBase.objects.filter(~Q(archetype=5) & ~Q(awaken=0) & Q(monster__stars=6)).prefetch_related('monster_set').values(
        'id', 'name').annotate(count=Count('monster__id')))  # archetype=5 -> Material Monsters, awaken=0 -> Unawakened, monster__stars=6 -> 6*
    monsters_base = sorted(
        monsters_base, key=itemgetter('count'), reverse=True)

    context = {
        'base': monsters_base,
    }

    return render(request, 'website/report/report_index.html', context)


def get_old_reports(request):
    images = dict()

    app_static_dir = os.path.join(
        settings.BASE_DIR, 'website', 'static', 'website', 'reports')

    for filename in os.listdir(app_static_dir):
        if filename.endswith(".png"):
            images[filename] = os.path.getmtime(
                app_static_dir + '/' + filename)

    images = {k: v for k, v in sorted(images.items(
    ), key=lambda image: image[1], reverse=True)}  # reverse=True -> descending
    for key, val in images.items():
        images[key] = datetime.strftime(
            datetime.fromtimestamp(val), "%Y-%m-%d")

    context = {
        'images': images,
    }

    return render(request, 'website/report/report_old.html', context)


def create_monster_report_by_bot(monster_id):
    base_monster = MonsterBase.objects.get(id=monster_id)

    monsters, hoh_exist, hoh_date, fusion_exist, filename, monsters_runes, monster_family, monsters_artifacts = get_monster_info(
        base_monster)

    try:
        plots, most_common_builds, plot_sets, plot_builds, top_sets, plot_artifact_element_main, plot_artifact_archetype_main, artifact_best = generate_plots(monsters, monsters_runes, base_monster, monsters_artifacts, True)
    except KeyError as e:  # no results
        plots = None
        most_common_builds = 'No information given'
        plot_sets = None
        plot_builds = None
        top_sets = None
        plot_artifact_element_main = None
        plot_artifact_archetype_main = None
        artifact_best = None

    context = {
        'base_monster': base_monster,
        'monsters': monsters,
        'family': monster_family,
        'hoh': hoh_exist,
        'hoh_date': hoh_date,
        'fusion': fusion_exist,
        'plots': plots,
        'most_common_builds': most_common_builds,
        'date_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'plot_sets': plot_sets,
        'plot_builds': plot_builds,
        'top_sets': top_sets,
        'plot_artifacts_element_main': plot_artifact_element_main,
        'plot_artifacts_archetype_main': plot_artifact_archetype_main,
        'artifact_best': artifact_best,
    }

    html = render_to_string('website/report/report_bot_generate.html', context)

    try:
        html_file = open("website/bot/monsters/" +
                         str(monster_id) + '.html', "w")
        html_file.write(html)
        html_file.close()
        return True
    except:
        return False
