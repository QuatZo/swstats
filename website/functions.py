from .models import *
from django.db.models import F, Q, Avg, Min, Max, Sum, Count, FloatField

import copy
import math
import datetime
import logging
import matplotlib.cm as cm
import numpy as np

########################################################## UPLOAD #########################################################
# region RUNES
def calc_efficiency(rune):
    primary = rune['pri_eff']
    innate = rune['prefix_eff']
    substats = rune['sec_eff']

    # TYPE: [ 1*, 2*, 3*, 4*, 5*, 6* ]
    MAINSTAT_MAX = {
        1: [ 804, 1092, 1380, 1704, 2088, 2448 ],
        2: [ 18, 20, 38, 43, 51, 63 ],
        3: [ 54, 74, 93, 113, 135, 160 ],
        4: [ 18, 20, 38, 43, 51, 63 ],
        5: [ 54, 74, 93, 113, 135, 160 ],
        6: [ 18, 20, 38, 43, 51, 63 ],

        8: [ 18, 19, 25, 30, 39, 42 ],
        9: [ 18, 20, 37, 41, 47, 58 ],
        10: [ 20, 37, 43, 58, 65, 80 ],
        11: [ 18, 20, 38, 44, 51, 64 ],
        12: [ 18, 20, 38, 44, 51, 64 ],
    }

    # TYPE: [ 1*, 2*, 3*, 4*, 5*, 6* ]
    SUBSTAT_MAX = {
        1: [ 300, 525, 825, 1125, 1500, 1875 ],
        2: [ 10, 15, 25, 30, 35, 40 ],
        3: [ 20, 25, 40, 50, 75, 100 ],
        4: [ 10, 15, 25, 30, 35, 40 ],
        5: [ 20, 25, 40, 50, 75, 100 ],
        6: [ 10, 15, 25, 30, 35, 40 ],

        8: [ 5, 10, 15, 20, 25, 30 ],
        9: [ 5, 10, 15, 20, 25, 30 ],
        10: [ 10, 15, 20, 25, 25, 35 ],
        11: [ 10, 15, 20, 25, 35, 40 ],
        12: [ 10, 15, 20, 25, 35, 40 ],
    }

    ratio = 0.00
    rune_class = rune['class'] % 10 # ancient runes
    rune_class -= 1 # because 1* - 6*, but indexes starts at 0

    # mainstat
    ratio += MAINSTAT_MAX[primary[0]][rune_class] / MAINSTAT_MAX[primary[0]][-1] # -1: last, the biggest one

    # innate
    if innate[0]: ratio += innate[1] / SUBSTAT_MAX[innate[0]][-1]

    # substats
    for sub in substats:
        ratio += (sub[1] + sub[3]) / SUBSTAT_MAX[sub[0]][-1]

    eff_curr = ratio / 2.8 * 100
    eff_max = eff_curr + max(math.ceil((12 - rune['upgrade_curr']) / 3), 0) * 0.2 / 2.8 * 100

    return round(eff_curr, 2), round(eff_max, 2)

def add_stat(stats, base_stats, stat, substat = False):
    stat_effect = stat[0]
    stat_value = stat[1] + stat[3] if substat else stat[1] # grinds for substats

    # PRIMARY STAT, FLAT VALUES (CRIT RATE, CRIT DMG, ACC & RES ARE FLAT [WHEN CALCULATING])
    if stat_effect == 0: pass
    elif stat_effect == 1: stats['hp'] += stat_value
    elif stat_effect == 3: stats['attack'] += stat_value
    elif stat_effect == 5: stats['defense'] += stat_value
    elif stat_effect == 8: stats['speed'] += stat_value
    elif stat_effect == 9: stats['crit_rate'] += stat_value
    elif stat_effect == 10: stats['crit_dmg'] += stat_value
    elif stat_effect == 11: stats['res'] += stat_value
    elif stat_effect == 12: stats['acc'] += stat_value
    # PRIMARY STAT, % VALUES
    elif stat_effect == 2: stats['hp'] += stat_value * base_stats['hp'] / 100
    elif stat_effect == 4: stats['attack'] += stat_value * base_stats['attack'] / 100
    elif stat_effect == 6: stats['defense'] += stat_value * base_stats['defense'] / 100

def parse_rune(temp_rune, rune_lock=None):
    com2us_keys = ['rune_id', 'slot_no', 'rank', 'class', 'upgrade_curr', 'base_value', 'sell_value', 'extra']
    map_keys = ['id', 'slot', 'quality', 'stars', 'upgrade_curr', 'base_value', 'sell_value', 'quality_original']
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
            if sub[0] == 1: rune['sub_hp_flat'] = [sub[1], sub[3]]
            elif sub[0] == 2: rune['sub_hp'] = [sub[1], sub[3]]
            elif sub[0] == 3: rune['sub_atk_flat'] = [sub[1], sub[3]]
            elif sub[0] == 4: rune['sub_atk'] = [sub[1], sub[3]]
            elif sub[0] == 5: rune['sub_def_flat'] = [sub[1], sub[3]]
            elif sub[0] == 6: rune['sub_def'] = [sub[1], sub[3]]
            elif sub[0] == 8: rune['sub_speed'] = [sub[1], sub[3]]
            elif sub[0] == 9: rune['sub_crit_rate'] = [sub[1], sub[3]]
            elif sub[0] == 10: rune['sub_crit_dmg'] = [sub[1], sub[3]]
            elif sub[0] == 11: rune['sub_res'] = [sub[1], sub[3]]
            elif sub[0] == 12: rune['sub_acc'] = [sub[1], sub[3]]

        eff_curr, eff_max = calc_efficiency(temp_rune)
        rune['efficiency'] = eff_curr
        rune['efficiency_max'] = eff_max

    rune['equipped'] = True if 'occupied_type' in temp_rune_keys and temp_rune['occupied_type'] == 1 else False
    rune['locked'] = True if rune_lock is not None and 'rune_id' in temp_rune_keys and temp_rune['rune_id'] in rune_lock else False

    obj, created = Rune.objects.update_or_create( id=rune['id'], defaults=rune, )

def parse_runes_rta(rta_runes):
    for rta_rune in rta_runes:
        obj, created = RuneRTA.objects.update_or_create(rune=rta_rune['rune_id'], defaults={
            'monster': Monster.objects.get(id=rta_rune['occupied_id']),
            'rune': Rune.objects.get(id=rta_rune['rune_id']),
        })
# endregion

# region MONSTERS
def calc_stats(monster, runes):
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
        if rune['set_id'] not in sets.keys(): sets[rune['set_id']] = 1
        else: sets[rune['set_id']] += 1

        add_stat(stats, base_stats, rune['pri_eff'])
        add_stat(stats, base_stats, rune['prefix_eff'])
        for substat in rune['sec_eff']:
            add_stat(stats, base_stats, substat, True)
        
    for key, value in sets.items():
        _set = RuneSet.objects.get(id=key)
        set_number = math.floor(value / _set.amount)
        if set_number > 0:
            # bonus times number of completed sets
            if _set.name == 'Energy':
                stats['hp'] += base_stats['hp'] * set_number * 0.15 # Energy: +15% base HP
            elif _set.name == 'Guard':
                stats['defense'] += base_stats['defense'] * set_number * 0.15 # Guard: +15% base Defense
            elif _set.name == 'Swift':
                stats['speed'] += base_stats['speed'] * set_number * 0.25 # Swift: +25% base Speed
            elif _set.name == 'Blade':
                stats['crit_rate'] += set_number * 12 # Blade: +12% Critical Rate
            elif _set.name == 'Rage':
                stats['crit_dmg'] +=  set_number * 40 # Rage: +40% Critical Damage
            elif _set.name == 'Focus':
                stats['acc'] += set_number * 20 # Focus: +20% Accuracy
            elif _set.name == 'Endure':
                stats['res'] += set_number * 20 # Endure: +20% Resistance
            elif _set.name == 'Fatal':
                stats['attack'] += base_stats['attack'] * set_number * 0.35 # Fatal: +35% base Attack

    for stat in stats:
        stats[stat] = math.ceil(stats[stat])

    return stats

def parse_monster(temp_monster, buildings = list(), units_locked = list()):
    com2us_keys = ['unit_id', 'unit_level', 'class', 'create_time']
    map_keys = ['id', 'level', 'stars', 'created']
    temp_monster_keys = temp_monster.keys()
    monster = dict()

    for db, c2u in zip(map_keys, com2us_keys):
        if c2u in temp_monster_keys:
            monster[db] = temp_monster[c2u]

    monster['wizard'] = Wizard.objects.get(id=temp_monster['wizard_id'])
    monster['base_monster'] = MonsterBase.objects.get(id=temp_monster['unit_master_id'])

    ####################
    # Stats calc
    if 'runes' in temp_monster_keys:
        stats = calc_stats(temp_monster, temp_monster['runes'])
        monster['hp'] = stats['hp']
        monster['attack'] = stats['attack']
        monster['defense'] = stats['defense']
        monster['speed'] = stats['speed']
        monster['res'] = stats['res']
        monster['acc'] = stats['acc']
        monster['crit_rate'] = stats['crit_rate']
        monster['crit_dmg'] = stats['crit_dmg']

        monster_runes = [Rune.objects.get(id=rune['rune_id']) for rune in temp_monster['runes']]
        sum_eff = 0
        for monster_rune in monster_runes:
            sum_eff += monster_rune.efficiency
        monster['avg_eff'] = round(sum_eff / len(monster_runes), 2) if len(monster_runes) > 0 else 0.00
        monster['eff_hp'] = stats['hp'] * (1000 + (stats['defense'] * 3)) / 1000
        monster['eff_hp_def_break'] = stats['hp'] * (1000 + (stats['defense'] * 1.5)) / 1000
    ####################

    if 'skills' in temp_monster_keys:
        monster['skills'] = [skill[1] for skill in temp_monster['skills']]
    if 'source' in temp_monster_keys:
        monster['source'] = MonsterSource.objects.get(id=temp_monster['source'])
    monster['transmog'] = True if 'costume_master_id' in temp_monster_keys and temp_monster['costume_master_id'] else False
    monster['storage'] = False
    if 'building_id' in temp_monster_keys:
        for building in buildings:
            if building['building_id'] == temp_monster['building_id'] and building['building_master_id'] == 25:
                monster['storage'] = True
                break
    monster['locked'] = True if 'unit_id' in temp_monster_keys and temp_monster['unit_id'] in units_locked else False

    obj, created = Monster.objects.update_or_create( id=monster['id'], defaults=monster, )
    obj.runes.set(monster_runes)
    obj.save()

def parse_wizard_homunculus(homunculus):
    homies = dict()
    for el in homunculus:
        if el['unit_id'] not in homies.keys():
            homies[el['unit_id']] = dict()
            homies[el['unit_id']]['wizard'] = Wizard.objects.get(id=el['wizard_id'])
            homies[el['unit_id']]['homunculus'] = Monster.objects.get(id=el['unit_id'])
            homies[el['unit_id']]['depth_1'] = None
            homies[el['unit_id']]['depth_2'] =  None
            homies[el['unit_id']]['depth_3'] = None
            homies[el['unit_id']]['depth_4'] = None
            homies[el['unit_id']]['depth_5'] = None

        homies[el['unit_id']]['depth_' + str(el['skill_depth'])] = el['skill_id']

    for homie in homies.values():
        if None in homie.values():
            continue
        homie['build'] = HomunculusBuild.objects.get( depth_1=homie['depth_1'], depth_2=homie['depth_2'], depth_3=homie['depth_3'], depth_4=homie['depth_4'], depth_5=homie['depth_5'] )
        obj, created = WizardHomunculus.objects.update_or_create( wizard=homie['wizard'], homunculus=homie['homunculus'], defaults={
            'wizard': homie['wizard'],
            'homunculus': homie['homunculus'],
            'build': homie['build'],
        }, )
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
    obj, created = Guild.objects.update_or_create( id=guild['id'], defaults=guild, )
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
        obj, created = WizardBuilding.objects.update_or_create( wizard=building['wizard'], building=building['building'], defaults=building, )

    for deco in decos:
        building = dict()
        building['wizard'] = Wizard.objects.get(id=deco['wizard_id'])
        building['building'] = Building.objects.get(id=deco['master_id'])
        building['level'] = deco['level']
        obj, created = WizardBuilding.objects.update_or_create( wizard=building['wizard'], building=building['building'], defaults=building, )

def parse_wizard_inventory(inventory):
    for temp_item in inventory:
        try:
            item = dict()
            item['wizard'] = Wizard.objects.get(id=temp_item['wizard_id'])
            item['master_item'] = Item.objects.get(item_id=temp_item['item_master_id'], item_type=temp_item['item_master_type'])
            item['quantity'] = temp_item['item_quantity']
            obj, created = WizardItem.objects.update_or_create( wizard=item['wizard'], master_item=item['master_item'], defaults=item, )
        except Item.DoesNotExist:
            raise RecordDoesNotExist(f"Item with Master ID {temp_item['item_master_type']} & ID {temp_item['item_master_id']} is missing from Database.")

def parse_arena_records(pvp_info, defense_units, wizard_id):
    arena = dict()
    arena['wizard'] = Wizard.objects.get(id=wizard_id)
    arena['wins'] = pvp_info['arena_win']
    arena['loses'] = pvp_info['arena_lose']
    arena['rank'] = pvp_info['rating_id']
    for def_unit in defense_units:
        arena['def_' + str(def_unit['pos_id'])] = Monster.objects.get(id=def_unit['unit_id'])
    obj, created = Arena.objects.update_or_create( wizard=wizard_id, defaults=arena, )

def parse_decks(decks, wizard_id):
    for temp_deck in decks:
        try:
            deck = dict()
            deck['wizard'] = Wizard.objects.get(id=wizard_id)
            deck['place'] = temp_deck['deck_type']
            deck['number'] = temp_deck['deck_seq']
            deck['leader'] = Monster.objects.get(id=temp_deck['leader_unit_id'])
            deck_monsters = [Monster.objects.get(id=monster_id) for monster_id in temp_deck['unit_id_list'] if monster_id]
            temp_team_eff = [mon.avg_eff for mon in deck_monsters]
            deck['team_runes_eff'] = round(sum(temp_team_eff) / len(temp_team_eff), 2)
            obj, created = Deck.objects.update_or_create( wizard=wizard_id, place=temp_deck['deck_type'], number=temp_deck['deck_seq'], defaults=deck, )
            obj.monsters.set(deck_monsters)
            obj.save()
        except Monster.DoesNotExist as e:
            continue
# endregion

# region OTHER
logger = logging.getLogger(__name__)

def log_request_data(data):
    logger.debug(f"Error/Warning during upload occured for request: {json.dumps(data)}")

def has_banned_words(text):
    banned_words = [ 'like', 'crystal', 'button', 'thumb' ]

    if any(banned_word in text.lower() for banned_word in banned_words):
        return True
    
    return False

def log_exception(e, **kwargs):
    trace_back = traceback.format_exc()
    message = "Unexpected, UNHANDLED error has occured:\n" + str(e) + " " + str(trace_back)
    logger.error(message)
    logger.error(f"Error parts:", len(kwargs))
    for key, val in kwargs.items():
        logger.error(key)
        log_request_data(value)
# endregion

########################################################## VIEWS ##########################################################
# region RUNES - should be async and in tasks to speed things up even more
def get_rune_list_avg_eff(runes):
    """Return the avg efficiency of given runes, incl. these runes splitted into two sets (above & equal, below)."""
    if not runes.exists():
        return { 'above': [], 'below': [], 'avg': 0 }

    avg_eff = runes.aggregate(Avg('efficiency'))['efficiency__avg']
    avg_eff_above_runes = list()
    avg_eff_below_runes = list()

    for rune in runes:
        if rune.efficiency >= avg_eff:
            avg_eff_above_runes.append({
                'x': rune.id,
                'y': rune.efficiency
            })
        else:
            avg_eff_below_runes.append({
                'x': rune.id,
                'y': rune.efficiency
            })

    return { 'above': avg_eff_above_runes, 'below': avg_eff_below_runes, 'avg': avg_eff }

def get_rune_list_normal_distribution(runes, parts, count):
    """Return sets of runes in specific number of parts, to make Normal Distribution chart."""
    if not count:
        return { 'distribution': [], 'scope': [], 'interval': parts }

    min_eff = runes.aggregate(Min('efficiency'))['efficiency__min']
    max_eff = runes.aggregate(Max('efficiency'))['efficiency__max']
    delta = (max_eff - min_eff) / parts

    points = [round(min_eff + (delta / 2) + i * delta, 2) for i in range(parts)]
    distribution = [0 for _ in range(parts)]

    for rune in runes:
        for i in range(parts):
            left = round(points[i] - delta / 2, 2)
            right = round(points[i] + delta / 2, 2)
            if i == parts - 1:
                if rune.efficiency >= left and rune.efficiency <= right:
                    distribution[i] += 1
                    break
            elif rune.efficiency >= left and rune.efficiency < right:
                    distribution[i] += 1
                    break

    return { 'distribution': distribution, 'scope': points, 'interval': parts }

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
    group_by_set = runes.values('rune_set__name').annotate(total=Count('rune_set')).order_by('-total')
    set_name = list()
    set_count = list()

    for group in group_by_set:
        set_name.append(group['rune_set__name'])
        set_count.append(group['total'])

    return { 'name': set_name, 'quantity': set_count, 'length': len(set_name) }

def get_rune_list_grouped_by_slot(runes):
    """Return numbers, amount of slots and quantity of runes for every slot in given runes list."""
    group_by_slot = runes.values('slot').annotate(total=Count('slot')).order_by('slot')
    slot_number = list()
    slot_count = list()

    for group in group_by_slot:
        slot_number.append(group['slot'])
        slot_count.append(group['total'])

    return { 'number': slot_number, 'quantity': slot_count, 'length': len(slot_number) }

def get_rune_list_grouped_by_quality(runes):
    """Return names, amount of qualities and quantity of runes for every quality in given runes list."""
    group_by_quality = runes.values('quality').annotate(total=Count('quality')).order_by('-total')
    quality_name = list()
    quality_count = list()

    for group in group_by_quality:
        quality_name.append(Rune().get_rune_quality(group['quality']))
        quality_count.append(group['total'])

    return { 'name': quality_name, 'quantity': quality_count, 'length': len(quality_name) }

def get_rune_list_grouped_by_quality_original(runes):
    """Return names, amount of qualities and quantity of runes for every original quality in given runes list."""
    group_by_quality_original = runes.values('quality_original').annotate(total=Count('quality_original')).order_by('-total')
    quality_original_name = list()
    quality_original_count = list()

    for group in group_by_quality_original:
        quality_original_name.append(Rune().get_rune_quality(group['quality_original']))
        quality_original_count.append(group['total'])

    return { 'name': quality_original_name, 'quantity': quality_original_count, 'length': len(quality_original_name) }

def get_rune_list_grouped_by_main_stat(runes):
    """Return names, amount of qualities and quantity of runes for every main stat type in given runes list."""
    group_by_main_stat = runes.values('primary').annotate(total=Count('primary')).order_by('-total')
    main_stat_name = list()
    main_stat_count = list()

    for group in group_by_main_stat:
        main_stat_name.append(Rune().get_rune_primary(group['primary']))
        main_stat_count.append(group['total'])

    return { 'name': main_stat_name, 'quantity': main_stat_count, 'length': len(main_stat_name) }

def get_rune_list_grouped_by_stars(runes):
    """Return numbers, amount of stars and quantity of runes for every star in given runes list."""
    group_by_stars = runes.values('stars').annotate(total=Count('stars')).order_by('stars')
    stars = dict()
    stars_number = list()
    stars_count = list()

    for group in group_by_stars:
        temp_stars = group['stars'] % 10 # ancient runes have 11-16 stars, instead of 1-6
        if temp_stars not in stars.keys():
            stars[temp_stars] = 0
        stars[temp_stars] += group['total']

    for key, val in stars.items():
        stars_number.append(key)
        stars_count.append(val)

    return { 'number': stars_number, 'quantity': stars_count, 'length': len(stars_number) }
# endregion

# region SIEGE - should be async and in tasks to speed things up even more
def get_siege_records_group_by_family(records):
    """Return name, amount of families and quantity of monsters for every family in given siege records."""
    family_monsters = dict()
    
    for record in records:
        for monster in record.monsters.all():
            if monster.base_monster.family.name not in family_monsters.keys():
                family_monsters[monster.base_monster.family.name] = 0
            family_monsters[monster.base_monster.family.name] += 1

    family_monsters = {k: family_monsters[k] for k in sorted(family_monsters, key=family_monsters.get, reverse=True)}
    return { 'name': list(family_monsters.keys()), 'quantity': list(family_monsters.values()), 'length': len(family_monsters.keys()) }

def get_siege_records_group_by_ranking(records):
    """Return ranking, amount of records and quantity of records for every ranking in given siege records."""
    group_by_rank = records.values('wizard__guild__siege_ranking').annotate(total=Count('wizard__guild__siege_ranking')).order_by('-total')

    ranking_id = list()
    ranking_name = list()
    ranking_count = list()

    for group in group_by_rank:
        ranking_id.append(group['wizard__guild__siege_ranking'])
        ranking_name.append(Guild().get_siege_ranking_name(group['wizard__guild__siege_ranking']))
        ranking_count.append(group['total'])

    return { 'ids': ranking_id, 'name': ranking_name, 'quantity': ranking_count, 'length': len(ranking_id) }
# endregion

# region OTHER
def create_rgb_colors(length):
    """Return the array of 'length', which contains 'rgba(r, g, b, a)' strings for Chart.js."""
    return [ 'rgba(' + str(int(c[0]*255)) + ', ' + str(int(c[1]*255)) + ', ' + str(int(c[2]*255)) + ', ' + str(.35) + ')' for c in cm.rainbow(np.linspace(0, 1, length))]
# endregion

























































