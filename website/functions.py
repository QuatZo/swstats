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


def parse_rune(temp_rune, rune_lock=None):
    com2us_keys = ['rune_id', 'slot_no', 'rank', 'class',
                   'upgrade_curr', 'base_value', 'sell_value', 'extra']
    map_keys = ['id', 'slot', 'quality', 'stars', 'upgrade_curr',
                'base_value', 'sell_value', 'quality_original']
    rune = dict()
    temp_rune_keys = temp_rune.keys()

    for db, c2u in zip(map_keys, com2us_keys):
        if c2u in temp_rune_keys:
            rune[db] = temp_rune[c2u]

    if 'wizard_id' in temp_rune_keys:
        rune['wizard'] = Wizard.objects.get(id=temp_rune['wizard_id'])
    if 'set_id' in temp_rune_keys:
        rune['rune_set'] = RuneSet.objects.get(id=temp_rune['set_id'])

    if 'pri_eff' in temp_rune_keys:
        rune['primary'] = temp_rune['pri_eff'][0]
        rune['primary_value'] = temp_rune['pri_eff'][1]
    if 'prefix_eff' in temp_rune_keys:
        rune['innate'] = temp_rune['prefix_eff'][0]
        rune['innate_value'] = temp_rune['prefix_eff'][1]

    if 'sec_eff' in temp_rune_keys:
        for sub in temp_rune['sec_eff']:
            if sub[0] == 1:
                rune['sub_hp_flat'] = [sub[1], sub[3]]
            elif sub[0] == 2:
                rune['sub_hp'] = [sub[1], sub[3]]
            elif sub[0] == 3:
                rune['sub_atk_flat'] = [sub[1], sub[3]]
            elif sub[0] == 4:
                rune['sub_atk'] = [sub[1], sub[3]]
            elif sub[0] == 5:
                rune['sub_def_flat'] = [sub[1], sub[3]]
            elif sub[0] == 6:
                rune['sub_def'] = [sub[1], sub[3]]
            elif sub[0] == 8:
                rune['sub_speed'] = [sub[1], sub[3]]
            elif sub[0] == 9:
                rune['sub_crit_rate'] = [sub[1], sub[3]]
            elif sub[0] == 10:
                rune['sub_crit_dmg'] = [sub[1], sub[3]]
            elif sub[0] == 11:
                rune['sub_res'] = [sub[1], sub[3]]
            elif sub[0] == 12:
                rune['sub_acc'] = [sub[1], sub[3]]

        eff_curr, eff_max = calc_efficiency(temp_rune)
        rune['efficiency'] = eff_curr
        rune['efficiency_max'] = eff_max

    rune['equipped'] = True if 'occupied_type' in temp_rune_keys and temp_rune['occupied_type'] == 1 else False
    rune['locked'] = True if rune_lock is not None and 'rune_id' in temp_rune_keys and temp_rune['rune_id'] in rune_lock else False

    obj, created = Rune.objects.update_or_create(
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


def parse_artifact(temp_artifact):
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
        artifact['wizard'] = Wizard.objects.get(id=temp_artifact['wizard_id'])

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

    obj, created = Artifact.objects.update_or_create(
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
        return base_stats

    stats = copy.deepcopy(base_stats)

    sets = dict()
    for rune in runes:
        if rune['set_id'] not in sets.keys():
            sets[rune['set_id']] = 1
        else:
            sets[rune['set_id']] += 1

        add_stat(stats, base_stats, rune['pri_eff'])
        add_stat(stats, base_stats, rune['prefix_eff'])
        for substat in rune['sec_eff']:
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

    return stats


def parse_monster(temp_monster, buildings=list(), units_locked=list(), runes_rta=list(), artifacts_rta=list()):
    com2us_keys = ['unit_id', 'unit_level', 'class', 'create_time']
    map_keys = ['id', 'level', 'stars', 'created']
    temp_monster_keys = temp_monster.keys()
    monster = dict()

    for db, c2u in zip(map_keys, com2us_keys):
        if c2u in temp_monster_keys:
            monster[db] = temp_monster[c2u]

    monster['wizard'] = Wizard.objects.get(id=temp_monster['wizard_id'])
    monster['base_monster'] = MonsterBase.objects.get(
        id=temp_monster['unit_master_id'])

    ####################
    # Stats calc
    if 'runes' in temp_monster_keys:
        stats = calc_stats(
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
            id=rune['rune_id']) for rune in temp_monster['runes']]
        sum_eff = 0
        for monster_rune in monster_runes:
            sum_eff += monster_rune.efficiency
        monster['avg_eff'] = round(
            sum_eff / len(monster_runes), 2) if len(monster_runes) > 0 else 0.00
        monster['eff_hp'] = stats['hp'] * \
            (1140 + (stats['defense'] * 1 * 3.5)) / 1000
        monster['eff_hp_def_break'] = stats['hp'] * \
            (1140 + (stats['defense'] * .3 * 3.5)) / \
            1000  # defense break = -70% defense
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

    mon_runes_rta = [Rune.objects.get(id=r_id) for r_id in runes_rta]
    mon_artifacts_rta = [Artifact.objects.get(
        id=r_id) for r_id in artifacts_rta]

    obj, created = Monster.objects.update_or_create(
        id=monster['id'], defaults=monster, )
    obj.runes.set(monster_runes)
    obj.runes_rta.set(mon_runes_rta)
    obj.artifacts.set(monster_artifacts)
    obj.artifacts_rta.set(mon_artifacts_rta)
    obj.save()


def parse_wizard_homunculus(homunculus):
    homies = dict()
    for el in homunculus:
        if el['unit_id'] not in homies.keys():
            homies[el['unit_id']] = dict()
            homies[el['unit_id']]['wizard'] = Wizard.objects.get(
                id=el['wizard_id'])
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
    obj, created = Guild.objects.update_or_create(
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


def parse_wizard_buildings(decos, wizard_id):
    for temp_building in Building.objects.all():
        building = dict()
        building['wizard'] = Wizard.objects.get(id=wizard_id)
        building['building'] = temp_building
        building['level'] = 0
        obj, created = WizardBuilding.objects.update_or_create(
            wizard=building['wizard'], building=building['building'], defaults=building, )

    for deco in decos:
        building = dict()
        building['wizard'] = Wizard.objects.get(id=deco['wizard_id'])
        building['building'] = Building.objects.get(id=deco['master_id'])
        building['level'] = deco['level']
        obj, created = WizardBuilding.objects.update_or_create(
            wizard=building['wizard'], building=building['building'], defaults=building, )


def parse_arena_records(pvp_info, defense_units, wizard_id):
    arena = dict()
    arena['wizard'] = Wizard.objects.get(id=wizard_id)
    arena['wins'] = pvp_info['arena_win']
    arena['loses'] = pvp_info['arena_lose']
    arena['rank'] = pvp_info['rating_id']
    for def_unit in defense_units:
        arena['def_' + str(def_unit['pos_id'])
              ] = Monster.objects.get(id=def_unit['unit_id'])
    obj, created = Arena.objects.update_or_create(
        wizard=wizard_id, defaults=arena, )


def parse_decks(decks, wizard_id):
    for temp_deck in decks:
        try:
            deck = dict()
            deck['wizard'] = Wizard.objects.get(id=wizard_id)
            deck['place'] = temp_deck['deck_type']
            deck['number'] = temp_deck['deck_seq']
            deck['leader'] = Monster.objects.get(
                id=temp_deck['leader_unit_id'])
            deck_monsters = [Monster.objects.get(
                id=monster_id) for monster_id in temp_deck['unit_id_list'] if monster_id]
            temp_team_eff = [mon.avg_eff for mon in deck_monsters]
            deck['team_runes_eff'] = round(
                sum(temp_team_eff) / len(temp_team_eff), 2)
            obj, created = Deck.objects.update_or_create(
                wizard=wizard_id, place=temp_deck['deck_type'], number=temp_deck['deck_seq'], defaults=deck, )
            obj.monsters.set(deck_monsters)
            obj.save()
        except Monster.DoesNotExist as e:
            continue
# endregion


# region OTHER
logger = logging.getLogger(__name__)


def log_request_data(data):
    text = "Error/Warning during upload occured for request: " + \
        json.dumps(data)
    logger.debug(text)


def has_banned_words(text):
    banned_words = ['like', 'crystal', 'button', 'thumb']

    if any(banned_word in text.lower() for banned_word in banned_words):
        return True

    return False


def log_exception(e, **kwargs):
    trace_back = traceback.format_exc()
    message = "Unexpected, UNHANDLED error has occured:\n" + \
        str(e) + " " + str(trace_back)
    logger.error(message)
    logger.error(f"Error parts: {len(kwargs)}")
    for key, val in kwargs.items():
        logger.error(key)
        log_request_data(val)
# endregion

########################################################## VIEWS ##########################################################
# region RUNES


def get_rune_list_normal_distribution(runes, parts, count):
    """Return sets of runes in specific number of parts, to make Normal Distribution chart."""
    if not count:
        return {'distribution': [], 'scope': [], 'interval': parts}

    efficiencies = runes.values_list('efficiency', flat=True)
    min_eff = min(efficiencies)
    max_eff = max(efficiencies)

    delta = (max_eff - min_eff) / (parts + 1)
    if not delta:
        return {'distribution': [], 'scope': [], 'interval': parts}

    points = np.arange(min_eff, max_eff + delta, delta)

    distribution = np.histogram(efficiencies, bins=points)
    points = [round((points[i] + points[i+1])/2, 2)
              for i in range(len(points) - 1)]

    return {'distribution': distribution[0].tolist(), 'scope': points, 'interval': parts}


def get_rune_list_best(runes, x, count):
    """Return TopX (or all, if there is no X elements in list) efficient runes."""
    best_runes = runes.order_by('-efficiency')[:min(x, count)]
    return best_runes


def get_rune_list_fastest(runes, x, count):
    """Return TopX (or all, if there is no X elements in list) fastest runes."""
    fastest_runes = runes.order_by(F('sub_speed').desc(nulls_last=True))
    fastest_runes = fastest_runes[:min(x, count)]

    return fastest_runes


def get_rune_list_grouped_by_set(runes):
    """Return names, amount of sets and quantity of runes in every set in given runes list."""
    group_by_set = runes.values('rune_set__name').annotate(
        total=Count('rune_set')).order_by('-total')
    set_name = list()
    set_count = list()

    for group in group_by_set:
        set_name.append(group['rune_set__name'])
        set_count.append(group['total'])

    return {'name': set_name, 'quantity': set_count, 'length': len(set_name)}


def get_rune_list_grouped_by_slot(runes):
    """Return numbers, amount of slots and quantity of runes for every slot in given runes list."""
    group_by_slot = runes.values('slot').annotate(
        total=Count('slot')).order_by('slot')
    slot_number = list()
    slot_count = list()

    for group in group_by_slot:
        slot_number.append(group['slot'])
        slot_count.append(group['total'])

    return {'number': slot_number, 'quantity': slot_count, 'length': len(slot_number)}


def get_rune_list_grouped_by_quality(runes):
    """Return names, amount of qualities and quantity of runes for every quality in given runes list."""
    group_by_quality = runes.values('quality').annotate(
        total=Count('quality')).order_by('-total')
    quality_name = list()
    quality_count = list()

    for group in group_by_quality:
        quality_name.append(Rune().get_rune_quality(group['quality']))
        quality_count.append(group['total'])

    return {'name': quality_name, 'quantity': quality_count, 'length': len(quality_name)}


def get_rune_list_grouped_by_quality_original(runes):
    """Return names, amount of qualities and quantity of runes for every original quality in given runes list."""
    group_by_quality_original = runes.values('quality_original').annotate(
        total=Count('quality_original')).order_by('-total')
    quality_original_name = list()
    quality_original_count = list()

    for group in group_by_quality_original:
        quality_original_name.append(
            Rune().get_rune_quality(group['quality_original']))
        quality_original_count.append(group['total'])

    return {'name': quality_original_name, 'quantity': quality_original_count, 'length': len(quality_original_name)}


def get_rune_list_grouped_by_main_stat(runes):
    """Return names, amount of qualities and quantity of runes for every main stat type in given runes list."""
    group_by_main_stat = runes.values('primary').annotate(
        total=Count('primary')).order_by('-total')
    main_stat_name = list()
    main_stat_count = list()

    for group in group_by_main_stat:
        main_stat_name.append(Rune().get_rune_primary(group['primary']))
        main_stat_count.append(group['total'])

    return {'name': main_stat_name, 'quantity': main_stat_count, 'length': len(main_stat_name)}


def get_rune_list_grouped_by_stars(runes):
    """Return numbers, amount of stars and quantity of runes for every star in given runes list."""
    group_by_stars = runes.values('stars').annotate(
        total=Count('stars')).order_by('stars')
    stars = dict()
    stars_number = list()
    stars_count = list()

    for group in group_by_stars:
        # ancient runes have 11-16 stars, instead of 1-6
        temp_stars = group['stars'] % 10
        if temp_stars not in stars.keys():
            stars[temp_stars] = 0
        stars[temp_stars] += group['total']

    for key, val in stars.items():
        stars_number.append(key)
        stars_count.append(val)

    return {'number': stars_number, 'quantity': stars_count, 'length': len(stars_number)}


def get_rune_similar(runes, rune):
    """Return runes similar to the given one."""
    similar_runes = runes.filter(slot=rune.slot, rune_set=rune.rune_set, primary=rune.primary,
                                 upgrade_curr__gte=rune.upgrade_curr).exclude(id=rune.id).values_list('id', flat=True)
    max_count = min(50, len(similar_runes))
    return random.sample(list(similar_runes), max_count)
# endregion

# region ARTIFACTS


def get_artifact_list_grouped_by_rtype(artifacts):
    """Return names, amount of rtypes and quantity of artifact in every rtype in given artifacts list."""
    group_by_rtype = artifacts.values('rtype').annotate(
        total=Count('rtype')).order_by('-total')
    rtype_name = list()
    rtype_count = list()

    for group in group_by_rtype:
        rtype_name.append(Artifact().get_artifact_rtype(group['rtype']))
        rtype_count.append(group['total'])

    return {'name': rtype_name, 'quantity': rtype_count, 'length': len(rtype_name)}


def get_artifact_list_grouped_by_quality(artifacts):
    """Return names, amount of qualities and quantity of artifacts for every quality in given artifacts list."""
    group_by_quality = artifacts.values('quality').annotate(
        total=Count('quality')).order_by('-total')
    quality_name = list()
    quality_count = list()

    for group in group_by_quality:
        quality_name.append(Artifact().get_artifact_quality(group['quality']))
        quality_count.append(group['total'])

    return {'name': quality_name, 'quantity': quality_count, 'length': len(quality_name)}


def get_artifact_list_grouped_by_quality_original(artifacts):
    """Return names, amount of qualities and quantity of artifacts for every original quality in given artifacts list."""
    group_by_quality_original = artifacts.values('quality_original').annotate(
        total=Count('quality_original')).order_by('-total')
    quality_original_name = list()
    quality_original_count = list()

    for group in group_by_quality_original:
        quality_original_name.append(
            Artifact().get_artifact_quality(group['quality_original']))
        quality_original_count.append(group['total'])

    return {'name': quality_original_name, 'quantity': quality_original_count, 'length': len(quality_original_name)}


def get_artifact_list_grouped_by_primary(artifacts):
    """Return names, amount of primary and quantity of artifact in every primary in given artifacts list."""
    group_by_primary = artifacts.values('primary').annotate(
        total=Count('primary')).order_by('-total')
    primary_name = list()
    primary_count = list()

    for group in group_by_primary:
        primary_name.append(Artifact().get_artifact_primary(group['primary']))
        primary_count.append(group['total'])

    return {'name': primary_name, 'quantity': primary_count, 'length': len(primary_name)}


def get_artifact_list_grouped_by_attribute(artifacts):
    """Return names, amount of attribute and quantity of artifact in every attribute in given artifacts list."""
    group_by_attribute = artifacts.exclude(attribute=0).exclude(attribute__isnull=True).values(
        'attribute').annotate(total=Count('attribute')).order_by('-total')
    attribute_name = list()
    attribute_count = list()

    for group in group_by_attribute:
        attribute_name.append(
            Artifact().get_artifact_attribute(group['attribute']))
        attribute_count.append(group['total'])

    return {'name': attribute_name, 'quantity': attribute_count, 'length': len(attribute_name)}


def get_artifact_list_grouped_by_archetype(artifacts):
    """Return names, amount of archetype and quantity of artifact in every archetype in given artifacts list."""
    group_by_archetype = artifacts.exclude(archetype=0).exclude(archetype__isnull=True).values(
        'archetype').annotate(total=Count('archetype')).order_by('-total')
    archetype_name = list()
    archetype_count = list()

    for group in group_by_archetype:
        archetype_name.append(
            Artifact().get_artifact_archetype(group['archetype']))
        archetype_count.append(group['total'])

    return {'name': archetype_name, 'quantity': archetype_count, 'length': len(archetype_name)}


def get_artifact_similar(artifacts, artifact):
    """Return artifacts similar to the given one."""
    similar_artifacts = artifacts.filter(rtype=artifact.rtype, attribute=artifact.attribute,
                                         archetype=artifact.archetype).exclude(id=artifact.id).values_list('id', flat=True)
    MAX_COUNT = min(100, len(similar_artifacts))
    return random.sample(list(similar_artifacts), MAX_COUNT)
# endregion

# region MONSTERS - most of them should be async and in tasks to speed things up even more


def get_monster_list_over_time(monsters):
    """Return amount of monsters acquired over time."""

    if not monsters.exists():
        return {'time': [], 'quantity': []}

    LENGTH = 100
    temp_monsters = list(monsters.values_list('created', flat=True))
    temp_monsters.sort()

    to_timestamp = np.vectorize(lambda x: x.timestamp())
    time_stamps = to_timestamp(temp_monsters)
    start = time_stamps[0]
    end = time_stamps[-1]
    delta = (end - start) / (LENGTH + 1)
    time_values = np.arange(
        start, end + delta, delta) if monsters.count() > 1 else [start, start]

    distribution = np.histogram(time_stamps, bins=time_values)[0].tolist()

    time_values = [datetime.datetime.strftime(datetime.datetime.fromtimestamp(int(
        (time_values[i] + time_values[i+1])/2)), "%Y-%m-%d") for i in range(len(time_values) - 1)]

    return {'time': time_values, 'quantity': [sum(distribution[:i+1]) for i in range(len(distribution))]}


def get_monster_list_group_by_family(monsters):
    """Return name, amount of families and quantity of monsters for every family in given monsters list."""
    to_exclude = [142, 143, 182,
                  151]  # Angelmon, Rainbowmon, King Angelmon, Devilmon
    group_by_family = monsters.exclude(base_monster__family__in=to_exclude).values(
        'base_monster__family__name').annotate(total=Count('base_monster__family__name')).order_by('-total')

    family_name = list()
    family_count = list()

    for group in group_by_family:
        family_name.append(group['base_monster__family__name'])
        family_count.append(group['total'])

    return {'name': family_name, 'quantity': family_count, 'length': len(family_name)}


def get_monster_list_best(monsters, x, count):
    """Return TopX (or all, if there is no X elements in list) efficient monsters."""
    return monsters[:min(x, count)]


def get_monster_list_fastest(monsters, x, count):
    """Return TopX (or all, if there is no X elements in list) fastest monsters."""
    fastest_monsters = monsters.order_by(F('speed').desc(nulls_last=True))
    fastest_monsters = fastest_monsters[:min(x, count)]

    return fastest_monsters


def get_monster_list_group_by_attribute(monsters):
    """Return names, amount of attributes and quantity of monsters for every attribute in given monsters list."""
    group_by_attribute = monsters.values('base_monster__attribute').annotate(
        total=Count('base_monster__attribute')).order_by('-total')

    attribute_name = list()
    attribute_count = list()

    for group in group_by_attribute:
        attribute_name.append(MonsterBase(
            attribute=group['base_monster__attribute']).get_attribute_display())
        attribute_count.append(group['total'])

    return {'name': attribute_name, 'quantity': attribute_count, 'length': len(attribute_name)}


def get_monster_list_group_by_type(monsters):
    """Return names, amount of types and quantity of monsters for every type in given monsters list."""
    group_by_type = monsters.values('base_monster__archetype').annotate(
        total=Count('base_monster__archetype')).order_by('-total')

    type_name = list()
    type_count = list()

    for group in group_by_type:
        type_name.append(MonsterBase(
            archetype=group['base_monster__archetype']).get_archetype_display())
        type_count.append(group['total'])

    return {'name': type_name, 'quantity': type_count, 'length': len(type_name)}


def get_monster_list_group_by_base_class(monsters):
    """Return number, amount of base class and quantity of monsters for every base class in given monsters list."""
    group_by_base_class = monsters.values('base_monster__base_class').annotate(
        total=Count('base_monster__base_class')).order_by('base_monster__base_class')

    base_class_number = list()
    base_class_count = list()

    for group in group_by_base_class:
        base_class_number.append(group['base_monster__base_class'])
        base_class_count.append(group['total'])

    return {'number': base_class_number, 'quantity': base_class_count, 'length': len(base_class_number)}


def get_monster_list_group_by_storage(monsters):
    """Return amount of monsters in/out of storage monsters list."""
    group_by_storage = monsters.values('storage').annotate(
        total=Count('storage')).order_by('-total')

    storage_value = list()
    storage_count = list()

    for group in group_by_storage:
        storage_value.append(str(group['storage']))
        storage_count.append(group['total'])

    return {'value': storage_value, 'quantity': storage_count, 'length': len(storage_value)}


def get_monsters_hoh():
    monsters_hoh = [record['monster']
                    for record in MonsterHoh.objects.all().values('monster')]
    base_monsters_hoh = [record['id'] for record in MonsterBase.objects.filter(
        id__in=monsters_hoh).values('id')]
    base_monsters_hoh += [record + 10 for record in base_monsters_hoh]

    return base_monsters_hoh


def get_monsters_fusion():
    monster_fusion = [record['monster']
                      for record in MonsterFusion.objects.all().values('monster')]
    base_monsters_fusion = [record['id'] for record in MonsterBase.objects.filter(
        id__in=monster_fusion).values('id')]
    base_monsters_fusion += [record + 10 for record in base_monsters_fusion]

    return base_monsters_fusion


def get_monster_list_group_by_hoh(monsters):
    """Return amount of monsters which have been & and not in Hall of Heroes."""

    base_monsters_hoh = get_monsters_hoh()
    monsters_hoh = monsters.filter(base_monster__in=base_monsters_hoh).count()
    monsters_hoh_exclude = monsters.exclude(
        base_monster__in=base_monsters_hoh).count()

    hoh_values = list()
    hoh_quantity = list()

    if monsters_hoh > 0:
        hoh_values.append(True)
        hoh_quantity.append(monsters_hoh)

    if monsters_hoh_exclude > 0:
        hoh_values.append(False)
        hoh_quantity.append(monsters_hoh_exclude)

    return {'value': hoh_values, 'quantity': hoh_quantity, 'length': len(hoh_values)}


def get_monster_list_group_by_fusion(monsters):
    """Return amount of monsters which have been & and not in Fusion."""
    base_monsters_fusion = get_monsters_fusion()

    monsters_fusion = monsters.filter(
        base_monster__in=base_monsters_fusion).count()
    monsters_fusion_exclude = monsters.exclude(
        base_monster__in=base_monsters_fusion).count()

    fusion_values = list()
    fusion_quantity = list()

    if monsters_fusion > 0:
        fusion_values.append(True)
        fusion_quantity.append(monsters_fusion)

    if monsters_fusion_exclude > 0:
        fusion_values.append(False)
        fusion_quantity.append(monsters_fusion_exclude)

    return {'value': fusion_values, 'quantity': fusion_quantity, 'length': len(fusion_values)}


def get_monster_rank_avg_eff(monsters, monster):
    return monsters.filter(avg_eff__gte=monster.avg_eff).count()


def get_monster_rank_stats(monsters, monster, stat, count):
    """Return place of monster based on given stat."""
    stats = {
        'hp': monsters.filter(hp__gte=monster.hp).count(),
        'attack': monsters.filter(attack__gte=monster.attack).count(),
        'defense': monsters.filter(defense__gte=monster.defense).count(),
        'speed': monsters.filter(speed__gte=monster.speed).count(),
        'res': monsters.filter(res__gte=monster.res).count(),
        'acc': monsters.filter(acc__gte=monster.acc).count(),
        'crit_rate': monsters.filter(crit_rate__gte=monster.crit_rate).count(),
        'crit_dmg': monsters.filter(crit_dmg__gte=monster.crit_dmg).count(),
        'eff_hp': monsters.filter(eff_hp__gte=monster.eff_hp).count(),
        'eff_hp_def_break': monsters.filter(eff_hp_def_break__gte=monster.eff_hp_def_break).count(),
    }

    return stats[stat] + 1


def get_monster_records(monster):
    siege = monster.siege_defense_monsters.all()

    dungeons = monster.dungeon_monsters.values('dungeon', 'stage', 'win').annotate(
        ct=Count('id'), avg=Avg('clear_time')).order_by('dungeon', '-stage', 'win')
    dungs = dict()
    for d in dungeons:
        key = f"d{d['dungeon']}_s{d['stage']}"
        if key not in dungs.keys():
            dungs[key] = {'d_id': d['dungeon'], 'stage': d['stage'],
                          'wins': 0, 'loses': 0, 'avg_time': None}
        if d['win']:
            dungs[key]['wins'] = d['ct']
            dungs[key]['avg_time'] = d['avg']
        else:
            dungs[key]['loses'] = d['ct']

    raids = RaidDungeonRun.objects.all()
    raids_mon = dict()
    for i in range(1, 9):
        for run in raids.filter(**{f'monster_{i}': monster}).values('stage', 'win').annotate(ct=Count('battle_key'), avg=Avg('clear_time')).order_by('stage', 'win'):
            key = f's_{run["stage"]}'
            # {% include 'website/dungeons/dungeon_card_compressed.html' with dungeon=raid %}
            if key not in raids_mon.keys():
                raids_mon[key] = {'d_name': 'Rift of Worlds', 'd_url': 'rift-of-worlds',
                                  'stage': run['stage'], 'wins': 0, ' loses': 0, 'avg_time': None}
            if run['win']:
                raids_mon[key]['wins'] = run['ct']
                raids_mon[key]['avg_time'] = run['avg']
            else:
                raids_mon[key]['loses'] = run['ct']

    rifts = dict()
    rifts_obj = RiftDungeonRun.objects.all()
    for i in range(1, 9):
        rift_temp = rifts_obj.filter(**{f'monster_{i}': monster}).values('dungeon', 'win').annotate(
            ct=Count('battle_key'), avg=Avg('dmg_total')).order_by('dungeon', 'win')
        for run in rift_temp:
            key = f'dungeon_{run["dungeon"]}'
            if key not in rifts.keys():
                rifts[key] = {'dungeon': run["dungeon"],
                              'wins': 0, 'loses': 0, 'avg_dmg': None}
            if run['win']:
                rifts[key]['wins'] = run['ct']
                rifts[key]['avg_dmg'] = int(run['avg'])
            else:
                rifts[key]['loses'] = run['ct']

    return {
        'siege': siege,
        'dungeons': dungs,
        'rifts': rifts,
        'raids': raids_mon,
    }
# endregion

# region DECKS


def get_deck_list_group_by_family(decks):
    """Return name, amount of families and quantity of monsters for every family in given decks list."""
    family_monsters = dict()

    for deck in decks:
        for monster in deck.monsters.all():
            if monster.base_monster.family.name not in family_monsters.keys():
                family_monsters[monster.base_monster.family.name] = 0
            family_monsters[monster.base_monster.family.name] += 1

    family_monsters = {k: family_monsters[k] for k in sorted(
        family_monsters, key=family_monsters.get, reverse=True)}
    return {'name': list(family_monsters.keys()), 'quantity': list(family_monsters.values()), 'length': len(family_monsters.keys())}


def get_deck_list_group_by_place(decks):
    """Return names, amount of places and quantity of decks for every place in given decks list."""
    group_by_place = decks.values('place').annotate(
        total=Count('place')).order_by('-total')

    place_name = list()
    place_count = list()

    for group in group_by_place:
        place_name.append(Deck(place=group['place']).get_place_display())
        place_count.append(group['total'])

    return {'name': place_name, 'quantity': place_count, 'length': len(place_name)}


def get_deck_list_avg_eff(decks):
    """Return the avg efficiency of given deck, incl. decks splitted into two sets (above & equal, below)."""
    if not decks.count():
        return {'above': [], 'below': [], 'avg': 0}

    avg_eff = decks.aggregate(Avg('team_runes_eff'))['team_runes_eff__avg']
    avg_eff_above_decks = list()
    avg_eff_below_decks = list()

    for deck in decks:
        if deck.team_runes_eff >= avg_eff:
            avg_eff_above_decks.append({
                'x': deck.id,
                'y': deck.team_runes_eff
            })
        else:
            avg_eff_below_decks.append({
                'x': deck.id,
                'y': deck.team_runes_eff
            })

    return {'above': avg_eff_above_decks, 'below': avg_eff_below_decks, 'avg': avg_eff}


def get_deck_similar(deck, decks):
    return [temp_deck for temp_deck in decks if temp_deck.place == deck.place and temp_deck.id != deck.id and deck.team_runes_eff - 10 < temp_deck.team_runes_eff and deck.team_runes_eff + 10 > temp_deck.team_runes_eff]
# endregion

# region SIEGE


def get_siege_records_group_by_family(records):
    """Return name, amount of families and quantity of monsters for every family in given siege records."""
    family_monsters = dict()

    for record in records:
        for monster in record.monsters.all():
            if monster.base_monster.family.name not in family_monsters.keys():
                family_monsters[monster.base_monster.family.name] = 0
            family_monsters[monster.base_monster.family.name] += 1

    family_monsters = {k: family_monsters[k] for k in sorted(
        family_monsters, key=family_monsters.get, reverse=True)}
    return {'name': list(family_monsters.keys()), 'quantity': list(family_monsters.values()), 'length': len(family_monsters.keys())}


def get_siege_records_group_by_ranking(records):
    """Return ranking, amount of records and quantity of records for every ranking in given siege records."""
    group_by_rank = records.values('wizard__guild__siege_ranking').annotate(
        total=Count('wizard__guild__siege_ranking')).order_by('-total')

    ranking_id = list()
    ranking_name = list()
    ranking_count = list()

    for group in group_by_rank:
        ranking_id.append(group['wizard__guild__siege_ranking'])
        ranking_name.append(Guild().get_siege_ranking_name(
            group['wizard__guild__siege_ranking']))
        ranking_count.append(group['total'])

    return {'ids': ranking_id, 'name': ranking_name, 'quantity': ranking_count, 'length': len(ranking_id)}
# endregion

# region DUNGEONS


def get_dungeon_runs_distribution(runs, parts, raids=True):
    """Return sets of clear times in specific number of parts, to make Distribution chart."""
    if raids:
        if not runs.exists():
            return {'distribution': [], 'scope': [], 'interval': parts}
        runs_seconds = [clear_time.total_seconds() for clear_time in list(
            runs.values_list('clear_time', flat=True))]
    else:
        if not len(runs):
            return {'distribution': [], 'scope': [], 'interval': parts}
        runs_seconds = runs['clear_time'].dropna().dt.total_seconds()

    fastest = min(runs_seconds)
    slowest = max(runs_seconds)

    delta = (slowest - fastest) / (parts + 1)
    delta = max(1, delta)
    points = np.arange(fastest, slowest + delta, delta)

    distribution = np.histogram(runs_seconds, bins=points)[0].tolist()

    points = [str(timedelta(seconds=round((points[i] + points[i+1])/2)))
              for i in range(len(points) - 1)]

    return {'distribution': distribution, 'scope': points, 'interval': parts}


def get_dungeon_runs_by_comp(df, success_rate_min, success_rate_max):
    records = list()
    for comp, df_group in df.groupby('monsters'):
        avg_time = df_group['clear_time'].dropna().mean(
        ).total_seconds() if 'clear_time' in df_group.columns else np.nan

        if np.isnan(avg_time):
            continue

        runs_comp = df_group.shape[0]

        wins_comp = df_group[df_group['win'] == True].shape[0]

        record = {
            'comp': [int(c) for c in comp.split(', ')],
            'average_time': avg_time,
            'wins': wins_comp,
            'loses': runs_comp - wins_comp,
            'success_rate': round(wins_comp * 100 / runs_comp, 2),
        }

        if success_rate_min > 0 and record['success_rate'] < success_rate_min:
            continue
        if success_rate_max > 0 and record['success_rate'] > success_rate_max:
            continue

        # sort descending by 'ranking' formula: (cube_root(wins) * win_rate) / math.exp(average_time.total_seconds / (60 * fastest_run ))
        # 60 - seconds in one minute;
        # visualization for fastest_run = 15: https://www.wolframalpha.com/input/?i=y%2Fexp%28x%2F%2860*15%29%29+for+x%3D15..300%2C+y%3D0..1
        # visualization for difference between 100% success rate runs: https://www.wolframalpha.com/input/?i=sqrt%28z%29+*+1%2Fexp%28x%2F%2860*15%29%29+for+x%3D15..300%2C+z%3D1..1000
        record['sorting_val'] = round((min(record['wins'], 1000)**(1./3.) * record['success_rate'] / 100) / math.exp(
            record['average_time'] / (60 * df_group['clear_time'].dropna().min().total_seconds())), 4)
        minutes, seconds = divmod(int(record['average_time']), 60)
        minutes = '0' + \
            str(int(minutes)) if minutes < 10 else str(int(minutes))
        seconds = '0' + \
            str(int(seconds)) if seconds < 10 else str(int(seconds))
        record['average_time'] = minutes + ":" + seconds
        records.append(record)

    return records


def get_dungeon_runs_by_base_class(dungeon_runs):
    base_monsters = dict()
    for record in dungeon_runs.values_list('monsters__base_monster__name', flat=True):
        if record:
            if record not in base_monsters.keys():
                base_monsters[record] = 0
            base_monsters[record] += 1

    base_monsters = {k: base_monsters[k] for k in sorted(
        base_monsters, key=base_monsters.get, reverse=True)}
    return (list(base_monsters.keys()), list(base_monsters.values()))


def get_raid_dungeon_records_personal(dungeon_runs, fastest_run, success_rate_min, success_rate_max):
    records = list()
    comps = list()

    for run in dungeon_runs.values('monster_1', 'monster_2', 'monster_3', 'monster_4', 'monster_5', 'monster_6', 'monster_7', 'monster_8', 'leader'):
        if run in comps:
            continue
        comps.append(run)

        records_temp = dungeon_runs.filter(win__isnull=False, **run)
        records_count = records_temp.count()
        wins_count = records_temp.filter(win=True).count()
        avg_time = records_temp.filter(clear_time__isnull=False).aggregate(
            avg_time=Avg('clear_time'))['avg_time']

        record = {
            'frontline': [run[f'monster_{i}'] for i in range(1, 5)],
            'backline': [run[f'monster_{i}'] for i in range(5, 9)],
            'leader': run['leader'],
            'average_time': avg_time,
            'wins': wins_count,
            'loses': records_count - wins_count,
            'success_rate': round(wins_count * 100 / records_count, 2),
        }

        if success_rate_min > 0 and record['success_rate'] < success_rate_min:
            continue
        if success_rate_max > 0 and record['success_rate'] > success_rate_max:
            continue

        # sort descending by 'ranking' formula: (cube_root(wins) * win_rate) / math.exp(average_time.total_seconds / (60 * fastest_run ))
        # 60 - seconds in one minute;
        # visualization for fastest_run = 15: https://www.wolframalpha.com/input/?i=y%2Fexp%28x%2F%2860*15%29%29+for+x%3D15..300%2C+y%3D0..1
        # visualization for difference between 100% success rate runs: https://www.wolframalpha.com/input/?i=sqrt%28z%29+*+1%2Fexp%28x%2F%2860*15%29%29+for+x%3D15..300%2C+z%3D1..1000
        if record['average_time']:
            record['sorting_val'] = round((min(record['wins'], 1000)**(1./3.) * record['success_rate'] / 100) /
                                          math.exp(record['average_time'].total_seconds() / (60 * fastest_run)), 4)
        else:
            record['sorting_val'] = -1
        record['average_time'] = str(record['average_time'])
        records.append(record)

    return records


def get_raid_dungeon_runs_by_base_class(dungeon_runs):
    base_monsters = dict()
    monster_args = [f'monster_{i}__base_monster__name' for i in range(1, 9)]
    for record in dungeon_runs.values_list(*monster_args):
        for mon in list(set(record)):
            if mon:
                if mon not in base_monsters.keys():
                    base_monsters[mon] = 0
                base_monsters[mon] += 1

    base_monsters = {k: base_monsters[k] for k in sorted(
        base_monsters, key=base_monsters.get, reverse=True)}
    return (list(base_monsters.keys()), list(base_monsters.values()))


def get_rift_dungeon_damage_distribution(runs, parts):
    """Return sets of damages in specific number of parts, to make Distribution chart."""
    if not runs.exists():
        return {'distribution': [], 'scope': [], 'interval': parts}

    damages = [dmg_total for dmg_total in list(
        runs.values_list('dmg_total', flat=True))]
    lowest = min(damages)
    highest = max(damages)

    delta = (highest - lowest) / (parts + 1)
    delta = max(1, delta)
    points = np.arange(lowest, highest + delta, delta)

    distribution = np.histogram(damages, bins=points)[0].tolist()

    points = [str(int((points[i] + points[i+1])/2))
              for i in range(len(points) - 1)]

    return {'distribution': distribution, 'scope': points, 'interval': parts}


def get_rift_dungeon_records_personal(dungeon_runs, highest_damage, success_rate_min, success_rate_max):
    records = list()
    comps = list()

    for run in dungeon_runs.values('monster_1', 'monster_2', 'monster_3', 'monster_4', 'monster_5', 'monster_6', 'monster_7', 'monster_8', 'leader'):
        if run in comps:
            continue
        comps.append(run)

        records_temp = dungeon_runs.filter(win__isnull=False, **run)
        records_count = records_temp.count()
        wins_count = records_temp.filter(win=True).count()

        most_freq_rating = records_temp.values('win', 'clear_rating').annotate(
            wins=Count('clear_rating')).order_by('-wins').first()['clear_rating']
        dmg = records_temp.aggregate(max_dmg=Max(
            'dmg_total'), avg_dmg=Avg('dmg_total'))

        record = {
            'frontline': [run[f'monster_{i}'] for i in range(1, 5)],
            'backline': [run[f'monster_{i}'] for i in range(5, 9)],
            'leader': run['leader'],
            'most_freq_rating': RiftDungeonRun().get_rating_name(most_freq_rating),
            'wins': wins_count,
            'loses': records_count - wins_count,
            'success_rate': round(wins_count * 100 / records_count, 2),
            'dmg_best': round(dmg['max_dmg']),
            'dmg_avg': round(dmg['avg_dmg']),
        }

        if success_rate_min > 0 and record['success_rate'] < success_rate_min:
            continue
        if success_rate_max > 0 and record['success_rate'] > success_rate_max:
            continue

        # sort descending by 'ranking' formula: (cube_root(wins) * win_rate) / math.exp(average_time.total_seconds / (60 * fastest_run ))
        # 60 - seconds in one minute;
        # visualization for fastest_run = 15: https://www.wolframalpha.com/input/?i=y%2Fexp%28x%2F%2860*15%29%29+for+x%3D15..300%2C+y%3D0..1
        # visualization for difference between 100% success rate runs: https://www.wolframalpha.com/input/?i=sqrt%28z%29+*+1%2Fexp%28x%2F%2860*15%29%29+for+x%3D15..300%2C+z%3D1..1000
        record['sorting_val'] = round((min(record['wins'], 1000)**(1./3.) * record['success_rate'] / 100) / (
            math.exp((record['dmg_avg'] * most_freq_rating) / -(highest_damage * 12))), 4)
        records.append(record)

    return records


def get_rift_dungeon_runs_by_base_class(dungeon_runs):
    base_monsters = dict()
    monster_args = [f'monster_{i}__base_monster__name' for i in range(1, 9)]
    for record in dungeon_runs.values_list(*monster_args):
        for mon in list(set(record)):
            if mon:
                if mon not in base_monsters.keys():
                    base_monsters[mon] = 0
                base_monsters[mon] += 1

    base_monsters = {k: base_monsters[k] for k in sorted(
        base_monsters, key=base_monsters.get, reverse=True)}
    return (list(base_monsters.keys()), list(base_monsters.values()))

# endregion

# region DIMENSION HOLE DUNGEONS


def get_dimhole_runs_by_comp(df, success_rate_min, success_rate_max):
    records = list()
    for dung_stage, df_g in df.groupby(['dungeon', 'stage']):
        df_g_notna = df_g.dropna(how='all', axis=1)
        for comp, df_group in df_g_notna.groupby('monsters'):
            avg_time = df_group['clear_time'].dropna().mean().total_seconds(
            ) if 'clear_time' in df_group.columns else np.nan

            if np.isnan(avg_time):
                continue

            runs_comp = df_group.shape[0]
            wins_comp = df_group[df_group['win'] == True].shape[0]

            record = {
                'dungeon': DimensionHoleRun().get_dungeon_name(int(dung_stage[0])),
                'stage': int(dung_stage[1]),
                'comp': [int(c) for c in comp.split(', ')],
                'average_time': avg_time,
                'wins': wins_comp,
                'loses': runs_comp - wins_comp,
                'success_rate': round(wins_comp * 100 / runs_comp, 2),
            }

            if success_rate_min > 0 and record['success_rate'] < success_rate_min:
                continue
            if success_rate_max > 0 and record['success_rate'] > success_rate_max:
                continue

            # sort descending by 'ranking' formula: (cube_root(wins) * win_rate) / math.exp(average_time.total_seconds / (60 * fastest_run ))
            # 60 - seconds in one minute;
            # visualization for fastest_run = 15: https://www.wolframalpha.com/input/?i=y%2Fexp%28x%2F%2860*15%29%29+for+x%3D15..300%2C+y%3D0..1
            # visualization for difference between 100% success rate runs: https://www.wolframalpha.com/input/?i=sqrt%28z%29+*+1%2Fexp%28x%2F%2860*15%29%29+for+x%3D15..300%2C+z%3D1..1000
            record['sorting_val'] = round((min(record['wins'], 1000)**(1./3.) * record['success_rate'] / 100) / math.exp(
                record['average_time'] / (60 * df_group['clear_time'].dropna().min().total_seconds())), 4)
            minutes, seconds = divmod(int(record['average_time']), 60)
            minutes = '0' + \
                str(int(minutes)) if minutes < 10 else str(int(minutes))
            seconds = '0' + \
                str(int(seconds)) if seconds < 10 else str(int(seconds))
            record['average_time'] = minutes + ":" + seconds
            records.append(record)

    return records


def get_dimhole_runs_per_dungeon(dungeon_runs):
    """Return names, amount of dim hole dungeon types and runs quantity per dungeon."""
    group_by_dungeon = dungeon_runs.values('dungeon').annotate(
        total=Count('dungeon')).order_by('-total')

    dungeon_name = list()
    dungeon_count = list()

    for group in group_by_dungeon:
        dungeon_name.append(
            DimensionHoleRun().get_dungeon_name(group['dungeon']))
        dungeon_count.append(group['total'])

    return {'name': dungeon_name, 'quantity': dungeon_count, 'length': len(dungeon_name)}


def get_dimhole_runs_per_practice(dungeon_runs):
    """Return names, amount of dim hole dungeon types and runs quantity per practice mode."""
    group_by_practice = dungeon_runs.values('practice').annotate(
        total=Count('practice')).order_by('-total')

    dungeon_name = list()
    dungeon_count = list()

    for group in group_by_practice:
        dungeon_name.append(group['practice'])
        dungeon_count.append(group['total'])

    return {'name': dungeon_name, 'quantity': dungeon_count, 'length': len(dungeon_name)}


def get_dimhole_runs_per_stage(dungeon_runs):
    """Return names, amount of dim hole dungeon types and runs quantity per stage (difficulty, B1-B5)."""
    group_by_stage = dungeon_runs.values('stage').annotate(
        total=Count('stage')).order_by('-total')

    dungeon_name = list()
    dungeon_count = list()

    for group in group_by_stage:
        dungeon_name.append(group['stage'])
        dungeon_count.append(group['total'])

    return {'name': dungeon_name, 'quantity': dungeon_count, 'length': len(dungeon_name)}

# endregion

# region HOMUNCULUS


def get_homunculus_builds(homies):
    """Return names, amount of builds and quantity of homunculuses using specific build."""
    group_by_build = homies.values('build').annotate(
        total=Count('build')).order_by('build')

    build_name = list()
    build_identifier = list()
    build_count = list()

    for group in group_by_build:
        build_name.append(WizardHomunculus.get_build_display(group['build']))
        build_identifier.append(group['build'])
        build_count.append(group['total'])

    return {'name': build_name, 'quantity': build_count, 'length': len(build_name), 'identifier': build_identifier}


def get_homunculus_skill_description(homunculuses):
    """Return skills & theirs description for specific homie."""
    builds = homunculuses.prefetch_related('build', 'build__depth_1', 'build__depth_2',
                                           'build__depth_3', 'build__depth_4', 'build__depth_5', 'build__homunculus')
    unique_skills = list()

    for homie in builds:
        build = homie.build

        if build.depth_1 not in unique_skills:
            unique_skills.append(build.depth_1.id)
        if build.depth_2 not in unique_skills:
            unique_skills.append(build.depth_2.id)
        if build.depth_3 not in unique_skills:
            unique_skills.append(build.depth_3.id)
        if build.depth_4 not in unique_skills:
            unique_skills.append(build.depth_4.id)
        if build.depth_5 not in unique_skills:
            unique_skills.append(build.depth_5.id)

    return unique_skills
# endregion

# region OTHER


def create_rgb_colors(length, visible=False):
    """Return the array of 'length', which contains 'rgba(r, g, b, a)' strings for Chart.js. and 'rgba(r, g, b) for Plotly """
    if visible:
        return ['rgba(' + str(int(c[0]*255)) + ', ' + str(int(c[1]*255)) + ', ' + str(int(c[2]*255)) + ', ' + str(.8) + ')' for c in cm.rainbow(np.linspace(0, 1, length))]
    return ['rgba(' + str(int(c[0]*255)) + ', ' + str(int(c[1]*255)) + ', ' + str(int(c[2]*255)) + ', ' + str(.35) + ')' for c in cm.rainbow(np.linspace(0, 1, length))]


def get_scoring_system():
    points = {
        "wizard": {
            "active_contributor": {
                "base": 1000,
                "count": 0,
                "total": 0
            },
            "mana_100k": {
                "base": 1,
                "count": 0,
                "total": 0
            },
            "crystals_10": {
                "base": 1,
                "count": 0,
                "total": 0
            },
            "level": {
                "base": 5,
                "count": 0,
                "total": 0
            },
            "antibot_count": {
                "base": 1,
                "count": 0,
                "total": 0
            },
            "raid": {
                "base": 20,
                "count": 0,
                "total": 0
            },
            "storage_capacity": {
                "base": .25,
                "count": 0,
                "total": 0
            }
        },
        "guild": {
            "gw_rank":  {
                "base": 50,
                "count": 0,
                "total": 0
            },
            "siege_rank":  {
                "base": 50,
                "count": 0,
                "total": 0
            }
        },
        "buildings": {
            "max":  {
                "base": 20,
                "count": 0,
                "total": 0
            },
            "max_all":  {
                "base": 250,
                "count": 0,
                "total": 0
            }
        },
        "flags": {
            "max":  {
                "base": 50,
                "count": 0,
                "total": 0
            },
            "max_all":  {
                "base": 200,
                "count": 0,
                "total": 0
            }
        },
        "runes": {
            "count": {
                "base": .1,
                "count": 0,
                "total": 0
            },
            "stars_5_legend": {
                "base": 2,
                "count": 0,
                "total": 0
            },
            "stars_6_hero": {
                "base": 2,
                "count": 0,
                "total": 0
            },
            "stars_6_legend": {
                "base": 5,
                "count": 0,
                "total": 0
            },
            "upgrade_12": {
                "base": .1,
                "count": 0,
                "total": 0
            },
            "upgrade_15": {
                "base": .5,
                "count": 0,
                "total": 0
            },
            "sub_speed": [
                {
                    "base": 5,
                    "threshold": 20,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 15,
                    "threshold": 28,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 50,
                    "threshold": 33,
                    "count": 0,
                    "total": 0
                }
            ],
            "sub_hp": [
                {
                    "base": 5,
                    "threshold": 27,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 15,
                    "threshold": 35,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 50,
                    "threshold": 45,
                    "count": 0,
                    "total": 0
                }
            ],
            "sub_def": [
                {
                    "base": 5,
                    "threshold": 27,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 15,
                    "threshold": 35,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 50,
                    "threshold": 45,
                    "count": 0,
                    "total": 0
                }
            ],
            "sub_atk": [
                {
                    "base": 5,
                    "threshold": 27,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 15,
                    "threshold": 35,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 50,
                    "threshold": 45,
                    "count": 0,
                    "total": 0
                }
            ],
            "sub_crit_rate": [
                {
                    "base": 5,
                    "threshold": 20,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 15,
                    "threshold": 28,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 50,
                    "threshold": 33,
                    "count": 0,
                    "total": 0
                }
            ],
            "sub_crit_dmg": [
                {
                    "base": 5,
                    "threshold": 23,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 15,
                    "threshold": 27,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 50,
                    "threshold": 33,
                    "count": 0,
                    "total": 0
                }
            ]
        },
        "monsters": {
            "count": {
                "base": .1,
                "count": 0,
                "total": 0
            },
            "nat4": {
                "base": 2,
                "count": 0,
                "total": 0
            },
            "nat5": {
                "base": 5,
                "count": 0,
                "total": 0
            },
            "stars_6": {
                "base": 5,
                "count": 0,
                "total": 0
            },
            "transmog": {
                "base": 1,
                "count": 0,
                "total": 0
            },
            "with_runes": {
                "base": 1,
                "count": 0,
                "total": 0
            },
            "skillup": {
                "base": .1,
                "count": 0,
                "total": 0
            },
            "skillups_max": {
                "base": 5,
                "count": 0,
                "total": 0
            },
            "speed": [
                {
                    "base": 5,
                    "threshold": 200,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 15,
                    "threshold": 250,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 50,
                    "threshold": 300,
                    "count": 0,
                    "total": 0
                }
            ],
            "hp": [
                {
                    "base": 5,
                    "threshold": 30000,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 15,
                    "threshold": 37500,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 50,
                    "threshold": 45000,
                    "count": 0,
                    "total": 0
                }
            ],
            "defense": [
                {
                    "base": 5,
                    "threshold": 1500,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 15,
                    "threshold": 1875,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 50,
                    "threshold": 2250,
                    "count": 0,
                    "total": 0
                }
            ],
            "attack": [
                {
                    "base": 5,
                    "threshold": 1750,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 15,
                    "threshold": 2250,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 50,
                    "threshold": 2500,
                    "count": 0,
                    "total": 0
                }
            ],
            "crit_dmg": [
                {
                    "base": 5,
                    "threshold": 150,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 15,
                    "threshold": 200,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 50,
                    "threshold": 250,
                    "count": 0,
                    "total": 0
                }
            ],
            "crit_rate": [
                {
                    "base": 5,
                    "threshold": 70,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 15,
                    "threshold": 85,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 50,
                    "threshold": 100,
                    "count": 0,
                    "total": 0
                }
            ],
            "acc": [
                {
                    "base": 5,
                    "threshold": 45,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 15,
                    "threshold": 65,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 50,
                    "threshold": 85,
                    "count": 0,
                    "total": 0
                }
            ],
            "res": [
                {
                    "base": 5,
                    "threshold": 70,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 15,
                    "threshold": 85,
                    "count": 0,
                    "total": 0
                }, {
                    "base": 50,
                    "threshold": 100,
                    "count": 0,
                    "total": 0
                }
            ]
        },
        "total": {
            "wizard": 0,
            "guild": 0,
            "buildings": 0,
            "flags": 0,
            "runes": 0,
            "monsters": 0,
            "all": 0
        }
    }

    return points


def get_scoring_for_profile(wizard_id):
    points = get_scoring_system()
    wiz = Wizard.objects.get(id=wizard_id)
    runes = Rune.objects.filter(wizard=wiz)
    monsters = Monster.objects.filter(wizard=wiz).prefetch_related(
        'base_monster', 'runes', 'artifacts')
    buildings = WizardBuilding.objects.filter(
        wizard=wiz).prefetch_related('building')

    # active contributor
    dungeons = DungeonRun.objects.filter(wizard=wiz, date__gte=(
        datetime.datetime.now() - timedelta(days=7))).count()
    dimhole = DimensionHoleRun.objects.filter(wizard=wiz, date__gte=(
        datetime.datetime.now() - timedelta(days=7))).count()
    raids = RaidDungeonRun.objects.filter(wizard=wiz, date__gte=(
        datetime.datetime.now() - timedelta(days=7))).count()
    rifts = RiftDungeonRun.objects.filter(wizard=wiz, date__gte=(
        datetime.datetime.now() - timedelta(days=7))).count()

    points['wizard']['active_contributor']['count'] = 1 if dungeons + \
        dimhole + raids + rifts > 50 else 0
    ####

    # guild
    points['guild']['gw_rank']['count'] = math.floor(
        wiz.guild.gw_best_ranking / 1000) if wiz.guild.gw_best_ranking else 0
    points['guild']['siege_rank']['count'] = math.floor(
        wiz.guild.siege_ranking / 1000) if wiz.guild.siege_ranking else 0
    ####

    # wizard
    points['wizard']['mana_100k']['count'] = math.floor(wiz.mana / 100000)
    points['wizard']['crystals_10']['count'] = math.floor(wiz.crystals / 10)
    points['wizard']['level']['count'] = wiz.level

    points['wizard']['antibot_count']['count'] = wiz.antibot_count
    points['wizard']['raid']['count'] = wiz.raid_level
    points['wizard']['storage_capacity']['count'] = wiz.storage_capacity
    ####

    # buildings
    a_b_id = Building().get_area_id('Arena')
    a_b = buildings.filter(building__area=a_b_id)
    a_b_max_count = a_b.filter(level=10).count()
    points['buildings']['max']['count'] = a_b_max_count
    points['buildings']['max_all']['count'] = 1 if a_b_max_count == a_b.count() else 0
    ####

    # flags
    g_b_id = Building().get_area_id('Guild')
    g_b = buildings.filter(building__area=g_b_id)
    g_b_max_count = g_b.filter(level=10).count()
    points['flags']['max']['count'] = g_b_max_count
    points['flags']['max_all']['count'] = 1 if g_b_max_count == g_b.count() else 0
    ####

    # runes
    points['runes']['count']['count'] = runes.count()
    points['runes']['stars_5_legend']['count'] = runes.filter(
        stars=6, quality_original__in=[5, 15]).count()
    points['runes']['stars_6_hero']['count'] = runes.filter(
        stars=6, quality_original__in=[4, 14, 5, 15]).count()
    points['runes']['stars_6_legend']['count'] = runes.filter(
        stars=6, quality_original__in=[5, 15]).count()
    points['runes']['upgrade_12']['count'] = runes.filter(
        upgrade_curr__gte=12).count()
    points['runes']['upgrade_15']['count'] = runes.filter(
        upgrade_curr__gte=15).count()

    for rune in runes:
        spd = sum(rune.sub_speed) if rune.sub_speed is not None else 0
        hp = sum(rune.sub_hp) if rune.sub_hp is not None else 0
        atk = sum(rune.sub_atk) if rune.sub_atk is not None else 0
        defense = sum(rune.sub_def) if rune.sub_def is not None else 0
        crit_rate = sum(
            rune.sub_crit_rate) if rune.sub_crit_rate is not None else 0
        crit_dmg = sum(
            rune.sub_crit_dmg) if rune.sub_crit_dmg is not None else 0

        if spd:
            for pts in points['runes']['sub_speed']:
                if spd >= pts['threshold']:
                    pts['count'] += 1

        if hp:
            for pts in points['runes']['sub_hp']:
                if hp >= pts['threshold']:
                    pts['count'] += 1

        if atk:
            for pts in points['runes']['sub_atk']:
                if atk >= pts['threshold']:
                    pts['count'] += 1

        if defense:
            for pts in points['runes']['sub_def']:
                if defense >= pts['threshold']:
                    pts['count'] += 1

        if crit_rate:
            for pts in points['runes']['sub_crit_rate']:
                if crit_rate >= pts['threshold']:
                    pts['count'] += 1

        if crit_dmg:
            for pts in points['runes']['sub_crit_dmg']:
                if crit_dmg >= pts['threshold']:
                    pts['count'] += 1

    ####

    # monsters
    points['monsters']['count']['count'] = monsters.count()
    points['monsters']['nat4']['count'] = monsters.filter(
        base_monster__base_class=4).count()
    points['monsters']['nat5']['count'] = monsters.filter(
        base_monster__base_class=5).count()
    points['monsters']['stars_6']['count'] = monsters.filter(stars=6).count()
    points['monsters']['transmog']['count'] = monsters.filter(
        transmog=True).count()

    for monster in monsters:
        points['monsters']['with_runes']['count'] += 1 if monster.runes.count() == 6 else 0
        if monster.base_monster.archetype == 5:
            continue
        if monster.skills == monster.base_monster.max_skills:
            points['monsters']['skillups_max']['count'] += 1
        for skillup in monster.skills:
            points['monsters']['skillup']['count'] += skillup - 1

    for row in points['monsters']['speed']:
        row['count'] = monsters.filter(speed__gte=row['threshold']).count()
    for row in points['monsters']['hp']:
        row['count'] = monsters.filter(hp__gte=row['threshold']).count()
    for row in points['monsters']['attack']:
        row['count'] = monsters.filter(attack__gte=row['threshold']).count()
    for row in points['monsters']['defense']:
        row['count'] = monsters.filter(defense__gte=row['threshold']).count()
    for row in points['monsters']['crit_rate']:
        row['count'] = monsters.filter(crit_rate__gte=row['threshold']).count()
    for row in points['monsters']['crit_dmg']:
        row['count'] = monsters.filter(crit_dmg__gte=row['threshold']).count()
    for row in points['monsters']['res']:
        row['count'] = monsters.filter(res__gte=row['threshold']).count()
    for row in points['monsters']['acc']:
        row['count'] = monsters.filter(acc__gte=row['threshold']).count()
    ####

    for key in points.keys():
        if key == 'total':
            continue
        for _, val in points[key].items():
            if isinstance(val, list):
                for el in val:
                    el['total'] = round(el['count'] * el['base'], 2)
                    points['total'][key] += el['total']
                    points['total']['all'] += el['total']
            else:
                val['total'] = round(val['count'] * val['base'], 2)
                points['total'][key] += val['total']
                points['total']['all'] += val['total']

    for key in points['total'].keys():
        points['total'][key] = round(points['total'][key], 2)

    return points


def calc_monster_comparison_stats(id_, hp, attack, defense, speed, res, acc, crit_rate, crit_dmg, avg_eff_total, eff_hp, eff_hp_def_break, df_group, df_group_len, df_means):
    kw = {
        'hp': hp,
        'attack': attack,
        'defense': defense,
        'speed': speed,
        'res': res,
        'acc': acc,
        'crit_rate': crit_rate,
        'crit_dmg': crit_dmg,
        'avg_eff_total': avg_eff_total,
        'eff_hp': eff_hp,
        'eff_hp_def_break': eff_hp_def_break
    }
    m_stats = {
        'id': id_,
        'rank': dict()
    }
    for key, val in kw.items():
        m_stats['rank'][key] = {
            'top': round(len(df_group[df_group[key] > val]) / df_group_len * 100, 2),
            'avg': val - df_means[key],
        }

        if key == 'avg_eff_total':
            m_stats['rank'][key]['avg'] = round(m_stats['rank'][key]['avg'], 2)
        else:
            m_stats['rank'][key]['avg'] = int(
                round(m_stats['rank'][key]['avg']))

    return m_stats


def calc_rune_comparison_stats(id_, hp_f, hp, atk_f, atk, def_f, def_, spd, res, acc, c_rate, c_dmg, eff, df_group, df_group_len, df_means):
    kw = {
        'sub_hp_flat': hp_f,
        'sub_hp': hp,
        'sub_atk_flat': atk_f,
        'sub_atk': atk,
        'sub_def_flat': def_f,
        'sub_def': def_,
        'sub_speed': spd,
        'sub_res': res,
        'sub_acc': acc,
        'sub_crit_rate': c_rate,
        'sub_crit_dmg': c_dmg,
        'efficiency': eff
    }
    r_stats = {
        'id': id_,
        'rank': dict()
    }
    for key, val in kw.items():
        r_stats['rank'][key] = {
            'top': round(len(df_group[df_group[key] > val]) / df_group_len * 100, 2) if val else None,
            'avg': val - df_means[key] if val else None,
        }
        if key == 'efficiency':
            r_stats['rank'][key]['avg'] = round(r_stats['rank'][key]['avg'], 2)
        elif r_stats['rank'][key]['avg']:
            r_stats['rank'][key]['avg'] = int(
                round(r_stats['rank'][key]['avg']))

    return r_stats


def get_profile_comparison_with_database(wizard_id):
    monsters = Monster.objects.exclude(base_monster__archetype=5).exclude(base_monster__archetype=0).filter(
        stars=6).order_by('base_monster__name')  # w/o material, unknown; only 6*
    monsters_cols = ['id', 'wizard__id', 'base_monster__name', 'hp', 'attack', 'defense', 'speed',
                     'res', 'acc', 'crit_rate', 'crit_dmg', 'avg_eff_total', 'eff_hp', 'eff_hp_def_break']
    df_monsters = pd.DataFrame(monsters.values_list(
        *monsters_cols), columns=monsters_cols).drop_duplicates(subset=['id'])

    runes = Rune.objects.filter(upgrade_curr__gte=12).order_by(
        'slot', 'rune_set', '-quality_original')  # only +12-+15
    runes_kw = {
        'sub_hp_flat_sum': Func(F('sub_hp_flat'), function='unnest'),
        'sub_hp_sum': Func(F('sub_hp'), function='unnest'),
        'sub_atk_flat_sum': Func(F('sub_atk_flat'), function='unnest'),
        'sub_atk_sum': Func(F('sub_atk'), function='unnest'),
        'sub_def_flat_sum': Func(F('sub_def_flat'), function='unnest'),
        'sub_def_sum': Func(F('sub_def'), function='unnest'),
        'sub_speed_sum': Func(F('sub_speed'), function='unnest'),
        'sub_res_sum': Func(F('sub_res'), function='unnest'),
        'sub_acc_sum': Func(F('sub_acc'), function='unnest'),
        'sub_crit_rate_sum': Func(F('sub_crit_rate'), function='unnest'),
        'sub_crit_dmg_sum': Func(F('sub_crit_dmg'), function='unnest'),
    }
    runes = runes.annotate(**runes_kw)
    runes_cols = ['id', 'wizard__id', 'slot', 'rune_set__id', 'primary', 'efficiency',
                  'sub_hp_sum', 'sub_hp_flat_sum', 'sub_atk_sum', 'sub_atk_flat_sum', 'sub_def_sum', 'sub_def_flat_sum', 'sub_speed_sum',
                  'sub_res_sum', 'sub_acc_sum', 'sub_crit_rate_sum', 'sub_crit_dmg_sum']
    df_runes = pd.DataFrame(runes.values_list(*runes_cols), columns=[runes_col.replace(
        '_sum', '') for runes_col in runes_cols]).drop_duplicates(subset=['id']).fillna(0)

    comparison = {
        "monsters": [],
        "runes": [],
        "artifacts": [],
    }

    df_groups = df_monsters.groupby('base_monster__name', axis=0)
    for _, df_group in df_groups:
        df_wiz = df_group[df_group['wizard__id'] == wizard_id]
        df_means = df_group.mean()
        comparison['monsters'] += [calc_monster_comparison_stats(*row, df_group, len(df_group), df_means) for row in zip(df_wiz['id'], df_wiz['hp'], df_wiz['attack'], df_wiz['defense'],
                                                                                                                         df_wiz['speed'], df_wiz['res'], df_wiz['acc'], df_wiz['crit_rate'], df_wiz['crit_dmg'], df_wiz['avg_eff_total'], df_wiz['eff_hp'], df_wiz['eff_hp_def_break'])]

    df_groups = df_runes.groupby(['slot', 'rune_set__id', 'primary'])
    for _, df_group in df_groups:
        df_wiz = df_group[df_group['wizard__id'] == wizard_id]
        df_means = df_group.mean()
        comparison['runes'] += [calc_rune_comparison_stats(*row, df_group, len(df_group), df_means) for row in zip(df_wiz['id'], df_wiz['sub_hp_flat'], df_wiz['sub_hp'], df_wiz['sub_atk_flat'],
                                                                                                                   df_wiz['sub_atk'], df_wiz['sub_def_flat'], df_wiz['sub_def'], df_wiz['sub_speed'], df_wiz['sub_res'], df_wiz['sub_acc'], df_wiz['sub_crit_rate'], df_wiz['sub_crit_dmg'], df_wiz['efficiency'])]

    # Future Artifact Update
    # artifacts = Artifact.objects.all()
    # wiz_artifacts = Artifact.objects.filter(wizard=wiz)
    ########

    return comparison
# endregion
