from .models import *
from django.db.models import F, Q, Avg, Min, Max, Sum, Count, FloatField, Func

import copy
import math
import datetime
import logging
import matplotlib.cm as cm
import numpy as np
import pandas as pd
import traceback
import json
import random
import time
import os
from pathlib import Path

from datetime import timedelta

########################################################## UPLOAD #########################################################
# region RUNES


def calc_efficiency(rune):
    primary = rune['pri_eff']
    innate = rune['prefix_eff']
    substats = rune['sec_eff']

    # TYPE: [ 1*, 2*, 3*, 4*, 5*, 6* ]
    MAINSTAT_MAX = {
        1: [804, 1092, 1380, 1704, 2088, 2448],
        2: [18, 20, 38, 43, 51, 63],
        3: [54, 74, 93, 113, 135, 160],
        4: [18, 20, 38, 43, 51, 63],
        5: [54, 74, 93, 113, 135, 160],
        6: [18, 20, 38, 43, 51, 63],

        8: [18, 19, 25, 30, 39, 42],
        9: [18, 20, 37, 41, 47, 58],
        10: [20, 37, 43, 58, 65, 80],
        11: [18, 20, 38, 44, 51, 64],
        12: [18, 20, 38, 44, 51, 64],
    }

    # TYPE: [ 1*, 2*, 3*, 4*, 5*, 6* ]
    SUBSTAT_MAX = {
        1: [300, 525, 825, 1125, 1500, 1875],
        2: [10, 15, 25, 30, 35, 40],
        3: [20, 25, 40, 50, 75, 100],
        4: [10, 15, 25, 30, 35, 40],
        5: [20, 25, 40, 50, 75, 100],
        6: [10, 15, 25, 30, 35, 40],

        8: [5, 10, 15, 20, 25, 30],
        9: [5, 10, 15, 20, 25, 30],
        10: [10, 15, 20, 25, 25, 35],
        11: [10, 15, 20, 25, 35, 40],
        12: [10, 15, 20, 25, 35, 40],
    }

    ratio = 0.00
    rune_class = rune['class'] % 10  # ancient runes
    rune_class -= 1  # because 1* - 6*, but indexes starts at 0

    # mainstat
    ratio += MAINSTAT_MAX[primary[0]][rune_class] / \
        MAINSTAT_MAX[primary[0]][-1]  # -1: last, the biggest one

    # innate
    if innate[0]:
        ratio += innate[1] / SUBSTAT_MAX[innate[0]][-1]

    # substats
    for sub in substats:
        ratio += (sub[1] + sub[3]) / SUBSTAT_MAX[sub[0]][-1]

    eff_curr = ratio / 2.8 * 100
    eff_max = eff_curr + \
        max(math.ceil((12 - rune['upgrade_curr']) / 3), 0) * 0.2 / 2.8 * 100

    return round(eff_curr, 2), round(eff_max, 2)


def add_stat(stats, base_stats, stat, substat=False):
    stat_effect = stat[0]
    # grinds for substats
    stat_value = stat[1] + stat[3] if substat else stat[1]

    # PRIMARY STAT, FLAT VALUES (CRIT RATE, CRIT DMG, ACC & RES ARE FLAT [WHEN CALCULATING])
    if stat_effect == 0:
        pass
    elif stat_effect == 1:
        stats['hp'] += stat_value
    elif stat_effect == 3:
        stats['attack'] += stat_value
    elif stat_effect == 5:
        stats['defense'] += stat_value
    elif stat_effect == 8:
        stats['speed'] += stat_value
    elif stat_effect == 9:
        stats['crit_rate'] += stat_value
    elif stat_effect == 10:
        stats['crit_dmg'] += stat_value
    elif stat_effect == 11:
        stats['res'] += stat_value
    elif stat_effect == 12:
        stats['acc'] += stat_value
    # PRIMARY STAT, % VALUES
    elif stat_effect == 2:
        stats['hp'] += stat_value * base_stats['hp'] / 100
    elif stat_effect == 4:
        stats['attack'] += stat_value * base_stats['attack'] / 100
    elif stat_effect == 6:
        stats['defense'] += stat_value * base_stats['defense'] / 100


def parse_rune(temp_rune, wizard, rune_sets, rune_lock=None):
    com2us_keys = ['rune_id', 'slot_no', 'rank', 'class',
                   'upgrade_curr', 'base_value', 'sell_value', 'extra']
    map_keys = ['id', 'slot', 'quality', 'stars', 'upgrade_curr',
                'base_value', 'sell_value', 'quality_original']
    rune = dict()
    # some strange strings instead of dictionaries, happened only once since website launch
    if not isinstance(temp_rune, dict):
        return
    temp_rune_keys = temp_rune.keys()

    for db, c2u in zip(map_keys, com2us_keys):
        if c2u in temp_rune_keys:
            rune[db] = temp_rune[c2u]

    if 'wizard_id' in temp_rune_keys:
        rune['wizard'] = wizard
    if 'set_id' in temp_rune_keys:
        rune['rune_set'] = rune_sets[temp_rune['set_id']]

    if 'pri_eff' in temp_rune_keys:
        rune['primary'] = temp_rune['pri_eff'][0]
        rune['primary_value'] = temp_rune['pri_eff'][1]
    if 'prefix_eff' in temp_rune_keys:
        rune['innate'] = temp_rune['prefix_eff'][0]
        rune['innate_value'] = temp_rune['prefix_eff'][1]

    sub_map = {
        1: 'sub_hp_flat',
        2: 'sub_hp',
        3: 'sub_atk_flat',
        4: 'sub_atk',
        5: 'sub_def_flat',
        6: 'sub_def',
        8: 'sub_speed',
        9: 'sub_crit_rate',
        10: 'sub_crit_dmg',
        11: 'sub_res',
        12: 'sub_acc',
    }

    if 'sec_eff' in temp_rune_keys:
        for sub in temp_rune['sec_eff']:
            rune[sub_map[sub[0]]] = [sub[1], sub[3]]

        eff_curr, eff_max = calc_efficiency(temp_rune)
        rune['efficiency'] = eff_curr
        rune['efficiency_max'] = eff_max

    rune['equipped'] = True if 'occupied_type' in temp_rune_keys and temp_rune['occupied_type'] == 1 else False
    rune['locked'] = True if rune_lock is not None and 'rune_id' in temp_rune_keys and temp_rune['rune_id'] in rune_lock else False

    Rune.objects.update_or_create(
        id=rune['id'], defaults=rune, )

# endregion

# region ARTIFACTS


def calc_efficiency_artifact(artifact):
    substats = artifact['sec_effects']

    # TYPE: [ 1*, 2*, 3*, 4*, 5*, 6* ]
    SUBSTAT_MAX = {
        200: 30,
        201: 30,
        202: 30,
        203: 30,
        204: 20,
        205: 20,
        206: 30,
        207: 30,
        208: 15,
        209: 15,
        210: 15,
        211: 15,
        212: 20,
        213: 15,
        214: 15,
        215: 15,
        216: 15,
        217: 15,
        218: 15,
        219: 20,
        220: 20,
        221: 200,

        300: 20,
        301: 20,
        302: 20,
        303: 20,
        304: 20,
        305: 30,
        306: 30,
        307: 30,
        308: 30,
        309: 30,

        400: 30,
        401: 30,
        402: 30,
        403: 30,
        404: 30,
        405: 30,
        406: 30,
        407: 30,
        408: 30,
        409: 30,
    }

    ratio = 1.00

    # substats
    for sub in substats:
        ratio += sub[1] / SUBSTAT_MAX[sub[0]]

    eff_curr = ratio / 2.6 * 100
    eff_max = eff_curr + \
        max(math.ceil((12 - artifact['level']) / 3), 0) * 0.2 / 2.6 * 100

    return round(eff_curr, 2), round(eff_max, 2)


def parse_artifact(temp_artifact, wizard):
    com2us_keys = ['rid', 'type', 'attribute', 'unit_style',
                   'level', 'rank', 'natural_rank', 'locked']
    map_keys = ['id', 'rtype', 'attribute', 'archetype',
                'level', 'quality', 'quality_original', 'locked']
    artifact = dict()
    temp_artifact_keys = temp_artifact.keys()

    for db, c2u in zip(map_keys, com2us_keys):
        if c2u in temp_artifact_keys:
            artifact[db] = temp_artifact[c2u]

    if 'wizard_id' in temp_artifact_keys:
        artifact['wizard'] = wizard

    if 'pri_effect' in temp_artifact_keys and temp_artifact['pri_effect']:
        artifact['primary'] = temp_artifact['pri_effect'][0]
        artifact['primary_value'] = temp_artifact['pri_effect'][1]

    artifact['substats'] = []
    artifact['substats_values'] = []
    artifact['efficiency'] = 0.0
    artifact['efficiency_max'] = 0.0

    if 'sec_effects' in temp_artifact_keys and temp_artifact['sec_effects']:
        subs = []
        sub_values = []
        for sec_effect in temp_artifact['sec_effects']:
            subs.append(sec_effect[0])
            sub_values.append(sec_effect[1])

        artifact['substats'] = subs
        artifact['substats_values'] = sub_values

        eff_curr, eff_max = calc_efficiency_artifact(temp_artifact)
        artifact['efficiency'] = eff_curr
        artifact['efficiency_max'] = eff_max

    artifact['equipped'] = True if 'occupied_id' in temp_artifact_keys and temp_artifact['occupied_id'] > 0 else False

    Artifact.objects.update_or_create(
        id=artifact['id'], defaults=artifact, )
# endregion

# region MONSTERS


def calc_stats(monster, runes, artifacts):
    base_stats = {
        'hp': monster['con'] * 15,
        'attack': monster['atk'],
        'defense': monster['def'],
        'speed': monster['spd'],
        'res': monster['resist'],
        'acc': monster['accuracy'],
        'crit_rate': monster['critical_rate'],
        'crit_dmg': monster['critical_damage'],
    }

    if len(runes) == 0:
        return base_stats, []

    stats = copy.deepcopy(base_stats)

    sets = dict()
    rune_ids = list()
    for rune in runes:
        if isinstance(rune, dict):
            temp_rune = rune
        else:
            temp_rune = runes[rune]

        rune_ids.append(temp_rune['rune_id'])
        if temp_rune['set_id'] not in sets.keys():
            sets[temp_rune['set_id']] = 1
        else:
            sets[temp_rune['set_id']] += 1

        add_stat(stats, base_stats, temp_rune['pri_eff'])
        add_stat(stats, base_stats, temp_rune['prefix_eff'])
        for substat in temp_rune['sec_eff']:
            add_stat(stats, base_stats, substat, True)

    for artifact in artifacts:
        if 'pri_effect' in artifact and artifact['pri_effect']:
            if artifact['pri_effect'] == 100:
                stats['hp'] += temp_artifact['pri_effect'][1]
            elif artifact['pri_effect'] == 101:
                stats['attack'] += temp_artifact['pri_effect'][1]
            elif artifact['pri_effect'] == 102:
                stats['defense'] += temp_artifact['pri_effect'][1]

    for key, value in sets.items():
        _set = RuneSet.objects.get(id=key)
        set_number = math.floor(value / _set.amount)
        if set_number > 0:
            # bonus times number of completed sets
            if _set.name == 'Energy':
                stats['hp'] += base_stats['hp'] * \
                    set_number * 0.15  # Energy: +15% base HP
            elif _set.name == 'Guard':
                stats['defense'] += base_stats['defense'] * \
                    set_number * 0.15  # Guard: +15% base Defense
            elif _set.name == 'Swift':
                stats['speed'] += base_stats['speed'] * \
                    set_number * 0.25  # Swift: +25% base Speed
            elif _set.name == 'Blade':
                stats['crit_rate'] += set_number * \
                    12  # Blade: +12% Critical Rate
            elif _set.name == 'Rage':
                stats['crit_dmg'] += set_number * \
                    40  # Rage: +40% Critical Damage
            elif _set.name == 'Focus':
                stats['acc'] += set_number * 20  # Focus: +20% Accuracy
            elif _set.name == 'Endure':
                stats['res'] += set_number * 20  # Endure: +20% Resistance
            elif _set.name == 'Fatal':
                stats['attack'] += base_stats['attack'] * \
                    set_number * 0.35  # Fatal: +35% base Attack

    for stat in stats:
        stats[stat] = math.ceil(stats[stat])

    return stats, rune_ids


def parse_monster(temp_monster, wizard, buildings=list(), units_locked=list(), runes_rta=list(), artifacts_rta=list()):
    com2us_keys = ['unit_id', 'unit_level', 'class', 'create_time']
    map_keys = ['id', 'level', 'stars', 'created']
    temp_monster_keys = temp_monster.keys()
    monster = dict()

    for db, c2u in zip(map_keys, com2us_keys):
        if c2u in temp_monster_keys:
            monster[db] = temp_monster[c2u]

    monster['wizard'] = wizard
    monster['base_monster'] = MonsterBase.objects.get(
        id=temp_monster['unit_master_id'])

    ####################
    # Stats calc
    if 'runes' in temp_monster_keys:
        stats, rune_ids = calc_stats(
            temp_monster, temp_monster['runes'], temp_monster['artifacts'])
        monster['hp'] = stats['hp']
        monster['attack'] = stats['attack']
        monster['defense'] = stats['defense']
        monster['speed'] = stats['speed']
        monster['res'] = stats['res']
        monster['acc'] = stats['acc']
        monster['crit_rate'] = stats['crit_rate']
        monster['crit_dmg'] = stats['crit_dmg']

        monster_runes = [Rune.objects.get(
            id=rune_id) for rune_id in rune_ids]
        sum_eff = 0
        for monster_rune in monster_runes:
            sum_eff += monster_rune.efficiency
        monster['avg_eff'] = round(
            sum_eff / len(monster_runes), 2) if len(monster_runes) > 0 else 0.00
        monster['eff_hp'] = stats['hp'] * \
            (1140 + (stats['defense'] * 1 * 3.5)) / 1000
    else:
        monster_runes = list()
        monster['avg_eff'] = 0.00
    ####################

    if 'artifacts' in temp_monster_keys and temp_monster['artifacts']:
        monster_artifacts = [Artifact.objects.get(
            id=artifact['rid']) for artifact in temp_monster['artifacts']]
        sum_eff_artifacts = 0
        for monster_artifact in monster_artifacts:
            sum_eff_artifacts += monster_artifact.efficiency
        monster['avg_eff_artifacts'] = round(
            sum_eff_artifacts / len(monster_artifacts), 2) if len(monster_artifacts) > 0 else 0.00
    else:
        monster_artifacts = list()
        monster['avg_eff_artifacts'] = 0.00

    monster['avg_eff_total'] = 0.00
    eff_len = 0
    if 'avg_eff' in monster.keys():
        monster['avg_eff_total'] += monster['avg_eff'] * len(monster_runes)
        eff_len += len(monster_runes)
    if 'avg_eff_artifacts' in monster.keys() and monster['avg_eff_artifacts'] > 0:
        monster['avg_eff_total'] += monster['avg_eff_artifacts'] * \
            len(monster_artifacts)
        eff_len += len(monster_artifacts)
    monster['avg_eff_total'] = round(
        monster['avg_eff_total'] / eff_len, 2) if eff_len > 0 else 0.00

    if 'skills' in temp_monster_keys:
        monster['skills'] = [skill[1] for skill in temp_monster['skills']]
    if 'source' in temp_monster_keys:
        monster['source'] = MonsterSource.objects.get(
            id=temp_monster['source'])
    monster['transmog'] = True if 'costume_master_id' in temp_monster_keys and temp_monster['costume_master_id'] else False
    monster['storage'] = False
    if 'building_id' in temp_monster_keys:
        for building in buildings:
            if building['building_id'] == temp_monster['building_id'] and building['building_master_id'] == 25:
                monster['storage'] = True
                break
    monster['locked'] = True if 'unit_id' in temp_monster_keys and temp_monster['unit_id'] in units_locked else False

    mon_runes_rta = Rune.objects.filter(id__in=runes_rta)
    mon_artifacts_rta = Artifact.objects.filter(id__in=artifacts_rta)

    obj, _ = Monster.objects.update_or_create(
        id=monster['id'], defaults=monster, )
    obj.runes.set(monster_runes)
    obj.runes_rta.set(mon_runes_rta)
    obj.artifacts.set(monster_artifacts)
    obj.artifacts_rta.set(mon_artifacts_rta)
    obj.save()


def parse_wizard_homunculus(homunculus, wizard):
    homies = dict()
    for el in homunculus:
        if el['unit_id'] not in homies.keys():
            homies[el['unit_id']] = dict()
            homies[el['unit_id']]['wizard'] = wizard
            homies[el['unit_id']]['homunculus'] = Monster.objects.get(
                id=el['unit_id'])
            homies[el['unit_id']]['depth_1'] = None
            homies[el['unit_id']]['depth_2'] = None
            homies[el['unit_id']]['depth_3'] = None
            homies[el['unit_id']]['depth_4'] = None
            homies[el['unit_id']]['depth_5'] = None

        homies[el['unit_id']]['depth_' +
                              str(el['skill_depth'])] = el['skill_id']

    for homie in homies.values():
        if None in homie.values():
            continue
        if None in [homie['depth_1'], homie['depth_2'], homie['depth_3'], homie['depth_4'], homie['depth_5']]:
            continue
        try:
            homie['build'] = HomunculusBuild.objects.get(
                depth_1=homie['depth_1'], depth_2=homie['depth_2'], depth_3=homie['depth_3'], depth_4=homie['depth_4'], depth_5=homie['depth_5'])
            obj, created = WizardHomunculus.objects.update_or_create(wizard=homie['wizard'], homunculus=homie['homunculus'], defaults={
                'wizard': homie['wizard'],
                'homunculus': homie['homunculus'],
                'build': homie['build'],
            }, )
        except HomunculusBuild.DoesNotExist:
            pass

# endregion

# region GUILD


def parse_guild(guild_info, guildwar, tvalue):
    guild = dict()

    com2us_keys_guild = ['guild_id', 'level', 'member_now']
    map_keys_guild = ['id', 'level', 'members_amount']
    com2us_keys_best = ['rank', 'rating_id']
    map_keys_best = ['gw_best_place', 'gw_best_ranking']

    for db, c2u in zip(map_keys_guild, com2us_keys_guild):
        if c2u in guild_info.keys():
            guild[db] = guild_info[c2u]

    for db, c2u in zip(map_keys_best, com2us_keys_best):
        if c2u in guildwar.keys():
            guild[db] = guildwar[c2u]

    guild['last_update'] = datetime.datetime.utcfromtimestamp(tvalue)
    Guild.objects.update_or_create(
        id=guild['id'], defaults=guild, )
# endregion

# region WIZARD


def parse_wizard(temp_wizard, tvalue):
    com2us_keys = [
        'wizard_id', 'wizard_mana', 'wizard_crystal', 'wizard_crystal_paid', 'wizard_last_login', 'wizard_last_country', 'wizard_last_lang', 'wizard_level',
        'wizard_energy', 'energy_max', 'arena_energy', 'honor_point', 'guild_point', 'honor_medal', 'honor_mark', 'event_coin',
    ]
    map_keys = [
        'id', 'mana', 'crystals', 'crystals_paid', 'last_login', 'country', 'lang', 'level', 'energy', 'energy_max', 'arena_wing',
        'glory_point', 'guild_point', 'rta_point', 'rta_mark', 'event_coin',
    ]

    wizard = dict()
    for db, c2u in zip(map_keys, com2us_keys):
        if c2u in temp_wizard.keys():
            wizard[db] = temp_wizard[c2u]
    wizard['last_update'] = datetime.datetime.utcfromtimestamp(tvalue)

    return wizard


def parse_wizard_buildings(decos, wizard):
    buildings = {b.id: b for b in Building.objects.all()}
    wizard_buildings = {wb.building.id: wb for wb in WizardBuilding.objects.select_related(
        'building').filter(wizard=wizard)}
    wizard_buildings_new = {}
    wizard_buildings_update = []

    for b_id, temp_building in buildings.items():
        if b_id in wizard_buildings.keys() or wizard_buildings[b_id].level > 0:
            continue
        wizard_buildings_new[b_id] = WizardBuilding(
            wizard=wizard,
            level=0,
            building=temp_building,
        )

    for deco in decos:
        if deco['master_id'] in wizard_buildings.keys():
            temp_building = wizard_buildings[deco['master_id']]
            temp_building.level = deco['level']
            wizard_buildings_update.append(temp_building)
        else:
            wizard_buildings_new[deco['master_id']].level = deco['level']

    WizardBuilding.objects.bulk_update(wizard_buildings_update, ['level'])
    WizardBuilding.objects.bulk_create(wizard_buildings_new)


def parse_arena_records(pvp_info, defense_units, wizard):
    arena = dict()
    arena['wizard'] = wizard
    arena['wins'] = pvp_info['arena_win']
    arena['loses'] = pvp_info['arena_lose']
    arena['rank'] = pvp_info['rating_id']
    for def_unit in defense_units:
        arena['def_' + str(def_unit['pos_id'])
              ] = Monster.objects.get(id=def_unit['unit_id'])
    Arena.objects.update_or_create(
        wizard=wizard, defaults=arena, )


def parse_decks(decks, wizard):
    for temp_deck in decks:
        try:
            deck = dict()
            deck['wizard'] = wizard
            deck['place'] = temp_deck['deck_type']
            deck['number'] = temp_deck['deck_seq']
            deck['leader'] = Monster.objects.get(
                id=temp_deck['leader_unit_id'])
            deck_monsters = Monster.objects.filter(
                id__in=[monster_id for monster_id in temp_deck['unit_id_list'] if monster_id])
            temp_team_eff = [mon.avg_eff for mon in deck_monsters]
            deck['team_runes_eff'] = round(
                sum(temp_team_eff) / len(temp_team_eff), 2)
            obj, _ = Deck.objects.update_or_create(
                wizard=wizard, place=temp_deck['deck_type'], number=temp_deck['deck_seq'], defaults=deck, )
            obj.monsters.set(deck_monsters)
            obj.save()
        except Monster.DoesNotExist as e:
            continue
# endregion


# region OTHER
logger = logging.getLogger(__name__)


def create_rgb_colors(length, visible=False):
    """Return the array of 'length', which contains 'rgba(r, g, b, a)' strings for Chart.js. and 'rgba(r, g, b) for Plotly """
    if visible:
        return ['rgba(' + str(int(c[0]*255)) + ', ' + str(int(c[1]*255)) + ', ' + str(int(c[2]*255)) + ', ' + str(.8) + ')' for c in cm.rainbow(np.linspace(0, 1, length))]
    return ['rgba(' + str(int(c[0]*255)) + ', ' + str(int(c[1]*255)) + ', ' + str(int(c[2]*255)) + ', ' + str(.35) + ')' for c in cm.rainbow(np.linspace(0, 1, length))]


def log_request_data(fn, key, data, txt=False):
    folder = os.path.join(os.getcwd(), 'logs', 'json')
    Path(folder).mkdir(parents=True, exist_ok=True)
    ext = '.txt' if txt else '.json'
    filename = fn + key + ext

    full_path = os.path.join(folder, filename)
    with open(full_path, 'a+') as f:
        if txt:
            f.write(data)
        else:
            json.dump(data, f, indent=4)


def log_exception(e, **kwargs):
    trace_back = traceback.format_exc()
    message = "Unexpected, UNHANDLED error has occured:\n" + \
        str(e) + " " + str(trace_back)
    logger.error(message)
    logger.error(f"Error parts: {len(kwargs)}")
    filename = f'error-{datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}-'
    for key, val in kwargs.items():
        logger.error(key)
        log_request_data(filename, key, val)

    log_request_data(filename, 'traceback', str(trace_back), txt=True)
# endregion
