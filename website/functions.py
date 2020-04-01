from .models import *

import copy
import math
import datetime
import logging

############################# RUNES #############################
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

############################ MONSTERS ###########################
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

############################# GUILD #############################
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

############################# WIZARD ############################
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

############################# OTHER #############################
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