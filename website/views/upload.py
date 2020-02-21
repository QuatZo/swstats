from django.http import HttpResponse
from rest_framework import viewsets, permissions, status
import logging

from website.models import Wizard, RuneSet, Rune, MonsterFamily, MonsterBase, MonsterSource, Monster, MonsterRep, MonsterHoh, MonsterFusion, Deck, Building, WizardBuilding, Arena, HomunculusSkill, WizardHomunculus, Guild, RuneRTA, Item, WizardItem, DungeonRun, RaidBattleKey

import copy
import math
import datetime
import json

logger = logging.getLogger(__name__)

def log_request_data(data):
    logger.debug(f"Error/Warning during upload occured for request: {json.dumps(data)}")

# Create your views here.
class MonsterFamilyUploadViewSet(viewsets.ViewSet):
    def create(self, request):
        if request.data:
            for family in request.data:
                obj, created = MonsterFamily.objects.update_or_create( id=family['id'], defaults=family, )
            return HttpResponse(status=status.HTTP_201_CREATED)
        
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

class MonsterSourceUploadViewSet(viewsets.ViewSet):
    def create(self, request):
        if request.data:
            for source in request.data:
                obj, created = MonsterSource.objects.update_or_create( id=source['id'], defaults=source, )
            return HttpResponse(status=status.HTTP_201_CREATED)
        
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

class MonsterBaseUploadViewSet(viewsets.ViewSet):
     def create(self, request):
        if request.data:
            for base in request.data:
                monster_base = dict()
                ########################################
                # Monster Base Model
                monster_base['id'] = base['id']
                base['id'] = str(base['id'])
                monster_base['family'] = MonsterFamily.objects.get(id=int(base['id'][:-2]))
                monster_base['base_class'] = base['base_class']
                monster_base['name'] = base['name']
                monster_base['attribute'] = int(base['id'][-1])
                monster_base['archetype'] = base['archetype']
                monster_base['awaken'] = base['awaken']
                monster_base['max_skills'] = base['max_skills']
                ########################################

                obj, created = MonsterBase.objects.update_or_create( id=base['id'], defaults=monster_base, )
            return HttpResponse(status=status.HTTP_201_CREATED)
        
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

class MonsterHohUploadViewSet(viewsets.ViewSet):
    def create(self, request):
        if request.data:
            for hoh in request.data:
                monster_hoh = dict()
                ########################################
                # Monster HoH Model
                monster_hoh['monster'] = MonsterBase.objects.get(id=int(hoh['id']))
                monster_hoh['date_open'] = hoh['date_open']
                monster_hoh['date_close'] = hoh['date_close']
                ########################################

                obj, created = MonsterHoh.objects.update_or_create( monster=hoh['id'], defaults=monster_hoh, )
            return HttpResponse(status=status.HTTP_201_CREATED)
        
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

class MonsterFusionUploadViewSet(viewsets.ViewSet):
    def create(self, request):
        if request.data:
            for fusion in request.data:
                monster_fusion = dict()
                ########################################
                # Monster Fusion Model
                monster_fusion['monster'] = MonsterBase.objects.get(id=int(fusion['id']))
                monster_fusion['cost'] = fusion['cost']
                ########################################

                obj, created = MonsterFusion.objects.update_or_create( monster=fusion['id'], defaults=monster_fusion, )
            return HttpResponse(status=status.HTTP_201_CREATED)
        
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

class BuildingUploadViewSet(viewsets.ViewSet):
     def create(self, request):
        if request.data:
            for building in request.data:
                obj, created = Building.objects.update_or_create( id=building['id'], defaults=building, )
            return HttpResponse(status=status.HTTP_201_CREATED)
        
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

class HomunculusUploadViewSet(viewsets.ViewSet):
     def create(self, request):
        if request.data:
            for homie in request.data:
                obj, created = HomunculusSkill.objects.update_or_create( id=homie['id'], defaults=homie, )
            return HttpResponse(status=status.HTTP_201_CREATED)
        
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

class ItemUploadViewSet(viewsets.ViewSet):
     def create(self, request):
        if request.data:
            for temp_item in request.data:
                item = dict()
                ########################################
                # Item Model
                item['item_id'] = temp_item['item_master_id']
                item['item_type'] = temp_item['item_master_type']
                item['name'] = temp_item['name']
                ########################################

                obj, created = Item.objects.update_or_create( item_type=item['item_type'], item_id=item['item_id'], defaults=item, )
            return HttpResponse(status=status.HTTP_201_CREATED)
        
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

class UploadViewSet(viewsets.ViewSet):
    def calc_efficiency(self, rune):
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

    def add_stat(self, stats, base_stats, stat, substat = False):
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

    def calc_stats(self, monster, runes):
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

            self.add_stat(stats, base_stats, rune['pri_eff'])
            self.add_stat(stats, base_stats, rune['prefix_eff'])
            for substat in rune['sec_eff']:
                self.add_stat(stats, base_stats, substat, True)
            
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

    def parse_guild(self, guild_info, guildwar, tvalue):
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

    def parse_wizard(self, temp_wizard, tvalue):
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

    def parse_rune(self, temp_rune, rune_lock=None):
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

            eff_curr, eff_max = self.calc_efficiency(temp_rune)
            rune['efficiency'] = eff_curr
            rune['efficiency_max'] = eff_max

        rune['equipped'] = True if 'occupied_type' in temp_rune_keys and temp_rune['occupied_type'] == 1 else False
        rune['locked'] = True if rune_lock is not None and 'rune_id' in temp_rune_keys and temp_rune['rune_id'] in rune_lock else False

        obj, created = Rune.objects.update_or_create( id=rune['id'], defaults=rune, )

    def parse_monster(self, temp_monster, buildings = list(), units_locked = list()):
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
            stats = self.calc_stats(temp_monster, temp_monster['runes'])
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

    def parse_runes_rta(self, rta_runes):
        for rta_rune in rta_runes:
            if all(key in rta_rune.keys() for key_req in ['rune_id', 'occupied_id']):
                obj, created = RuneRTA.objects.update_or_create(rune=rta_rune['rune_id'], defaults={
                    'monster': Monster.objects.get(id=rta_rune['occupied_id']),
                    'rune': Rune.objects.get(id=rta_rune['rune_id']),
                })

    def parse_decks(self, decks, wizard_id):
        for temp_deck in decks:
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

    def parse_wizard_buildings(self, decos, wizard_id):
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

    def parse_arena_records(self, pvp_info, defense_units, wizard_id):
        arena = dict()
        arena['wizard'] = Wizard.objects.get(id=wizard_id)
        arena['wins'] = pvp_info['arena_win']
        arena['loses'] = pvp_info['arena_lose']
        arena['rank'] = pvp_info['rating_id']
        for def_unit in defense_units:
            arena['def_' + str(def_unit['pos_id'])] = Monster.objects.get(id=def_unit['unit_id'])
        obj, created = Arena.objects.update_or_create( wizard=wizard_id, defaults=arena, )

    def parse_wizard_homunculus(self, homunculus):
        homies = dict()
        for el in homunculus:
            if el['unit_id'] not in homies.keys():
                homies[el['unit_id']] = dict()
                homies[el['unit_id']]['wizard_id'] = Wizard.objects.get(id=el['wizard_id'])
                homies[el['unit_id']]['homunculus_id'] = Monster.objects.get(id=el['unit_id'])
                homies[el['unit_id']]['skill_1'] = None
                homies[el['unit_id']]['skill_1_plus'] =  None
                homies[el['unit_id']]['skill_2'] = None
                homies[el['unit_id']]['skill_2_plus'] = None
                homies[el['unit_id']]['skill_3'] = None

            if el['skill_depth'] == 1:
                homies[el['unit_id']]['skill_1'] = HomunculusSkill.objects.get(id=el['skill_id'])
            elif el['skill_depth'] == 2:
                homies[el['unit_id']]['skill_1_plus'] = HomunculusSkill.objects.get(id=el['skill_id'])
            elif el['skill_depth'] == 3:
                homies[el['unit_id']]['skill_2'] = HomunculusSkill.objects.get(id=el['skill_id'])
            elif el['skill_depth'] == 4:
                homies[el['unit_id']]['skill_2_plus'] = HomunculusSkill.objects.get(id=el['skill_id'])
            elif el['skill_depth'] == 5:
                homies[el['unit_id']]['skill_3'] = HomunculusSkill.objects.get(id=el['skill_id'])

        for homie in homies.values():
            obj, created = WizardHomunculus.objects.update_or_create( wizard_id=homie['wizard_id'], homunculus_id=homie['homunculus_id'], defaults=homie, )

    def parse_wizard_inventory(self, inventory):
        for temp_item in inventory:
            item = dict()
            item['wizard_id'] = Wizard.objects.get(id=temp_item['wizard_id'])
            item['master_item_id'] = Item.objects.get(item_id=temp_item['item_master_id'], item_type=temp_item['item_master_type'])
            item['quantity'] = temp_item['item_quantity']
            obj, created = WizardItem.objects.update_or_create( wizard_id=item['wizard_id'], master_item_id=item['master_item_id'], defaults=item, )

    def handle_profile_upload(self, data):
        logger.debug(f"Checking if guild {data['guild']['guild_info']['guild_id']} exists...")
        guild = Guild.objects.filter(id=data['guild']['guild_info']['guild_id'])
        guild_uptodate = False
        if guild.exists():
            logger.debug(f"Guild {data['guild']['guild_info']['guild_id']} exists... Checking if it's up-to-date...")
            guild = guild.filter(last_update__gte=datetime.datetime.utcfromtimestamp(data['tvalue']))
            if guild.exists():
                logger.debug(f"Guild {data['guild']['guild_info']['guild_id']} profile is up-to-date.")
                guild_uptodate = True
            else:
                logger.debug(f"Updating guild profile {data['guild']['guild_info']['guild_id']}")
        else:
            logger.debug(f"Guild profile does NOT exists. Starting first-time guild profile upload for {data['guild']['guild_info']['guild_id']}")

        if not guild_uptodate:
            self.parse_guild(data['guild']['guild_info'], data['guildwar_ranking_stat']['best'], data['tvalue'])

        logger.debug(f"Checking if profile {data['wizard_info']['wizard_name']} (ID: {data['wizard_info']['wizard_id']}) exists...")
        wiz = Wizard.objects.filter(id=data['wizard_info']['wizard_id'])
        wizard_uptodate = False
        if wiz.exists():
            logger.debug(f"Profile {data['wizard_info']['wizard_name']} (ID: {data['wizard_info']['wizard_id']}) exists... Checking if it's up-to-date...")
            wizard = wiz.filter(last_update__gte=datetime.datetime.utcfromtimestamp(data['tvalue']))
            if wizard.exists():
                logger.debug(f"Wizard profile {data['wizard_info']['wizard_name']} (ID: {data['wizard_info']['wizard_id']}) is up-to-date")
                wizard_uptodate = True
            else:
                logger.debug(f"Updating profile {data['wizard_info']['wizard_name']} (ID: {data['wizard_info']['wizard_id']})")
        else:
            logger.debug(f"Profile {data['wizard_info']['wizard_name']} (ID: {data['wizard_info']['wizard_id']}) does NOT exists. Starting first-time profile upload")

        if wizard_uptodate:
            return HttpResponse(status=status.HTTP_200_OK)

        temp_wizard = data['wizard_info']
        temp_runes = data['runes']
        for monster in data['unit_list']:
            for rune in monster['runes']:
                temp_runes.append(rune)
        ########################################
        # Wizard Model
        wizard = self.parse_wizard(temp_wizard, data['tvalue'])
        try:
            wizard['antibot_count'] = data['quiz_reward_info']['reward_count']
            wizard['raid_level'] = data['raid_info_list'][0]['available_stage_id']
            wizard['storage_capacity'] = data['unit_depository_slots']['number']
        except KeyError:
            logger.info("[Wizard]: No info about anti bot feature, raid level nor storage capacity")
        wizard_guilds = Guild.objects.filter(id=data['guild']['guild_info']['guild_id'])
        if wizard_guilds.count() > 0:
            wizard['guild'] = wizard_guilds.first()
        obj, created = Wizard.objects.update_or_create( id=wizard['id'], defaults=wizard, )
        ########################################

        for temp_rune in temp_runes:
            self.parse_rune(temp_rune, data['rune_lock_list'])

        for temp_monster in data['unit_list']:
            self.parse_monster(temp_monster, data['building_list'], data['unit_lock_list'])

        if 'world_arena_rune_equip_list' in data.keys():
            self.parse_runes_rta(data['world_arena_rune_equip_list'])
        else:
            logger.warning("Given JSON file is before an RTA Rune Management Update!")
            log_request_data(request.data)

        # monster rep
        obj, created = MonsterRep.objects.update_or_create( wizard_id=wizard['id'], defaults={
            'wizard_id': Wizard.objects.get(id=wizard['id']), 
            'monster_id': Monster.objects.get(id=temp_wizard['rep_unit_id'])
        }, )

        self.parse_decks(data['deck_list'], wizard['id'])
        self.parse_wizard_buildings(data['deco_list'], wizard['id'])
        self.parse_arena_records(data['pvp_info'], data['defense_unit_list'], wizard['id'])
        self.parse_wizard_homunculus(data['homunculus_skill_list'])
        self.parse_wizard_inventory(data['inventory_info'])

        logger.debug(f"Fully uploaded profile for {data['wizard_info']['wizard_name']} (ID: {data['wizard_info']['wizard_id']})")

    def handle_raid_start_upload(self, data):
        logger.debug(f"New Raid has been started")
        obj, created = RaidBattleKey.objects.get_or_create(battle_key=data['battle_info']['battle_key'], defaults={
            'battle_key': data['battle_info']['battle_key'],
            'stage': data['battle_info']['room_info']['stage_id'],
        })
        logger.debug(f"Created new Raid key")

    def handle_dungeon_run_upload(self, data_resp, data_req):
        command = data_resp['command']
        logger.debug(f"Starting Battle Dungeon Result upload for {data_resp['wizard_info']['wizard_name']} (ID: {data_resp['wizard_info']['wizard_id']})")
        dungeon = dict()
        wizard, created = Wizard.objects.update_or_create(id=data_resp['wizard_info']['wizard_id'], defaults=self.parse_wizard(data_resp['wizard_info'], data_resp['tvalue']))
        dungeon['wizard_id'] = Wizard.objects.get(id=data_resp['wizard_info']['wizard_id'])
        if command == 'BattleRiftOfWorldsRaidResult':
            dungeon['dungeon'] = 999999999
            rift_battles = RaidBattleKey.objects.filter(battle_key=data_req['battle_key'])
            if not rift_battles.count():
                logging.error(f"Unknown stage for Rift Raid Battle (ID: {data_req['battle_key']})")
                return False
            dungeon['stage'] = rift_battles.first().stage
        else:
            dungeon['dungeon'] = data_req['dungeon_id']
            dungeon['stage'] = data_req['stage_id']
        dungeon['date'] = datetime.datetime.utcfromtimestamp(data_resp['tvalue'])
        
        if data_resp['win_lose'] == 1:
            dungeon['win'] = True
            time_str = str(data_resp['clear_time']['current_time'])
            _time = {
                'hour': 0 if int(time_str[:-3]) < 3600 else round(int(time_str[:-3]) / 3600),
                'minute': 0 if int(time_str[:-3]) < 60 else round(int(time_str[:-3]) / 60),
                'second': int(time_str[:-3]) if int(time_str[:-3]) < 60 else int(time_str[:-3]) % 60,
                'microsecond': int(time_str[-3:]) * 1000,
            }
            dungeon['clear_time'] = datetime.time(_time['hour'], _time['minute'], _time['second'], _time['microsecond'])
        else:
            dungeon['win'] = False
            
        monsters = list()
        # whole info (with runes) is in response data, but by unknown reason sometimes it's a good JSON, sometimes bad
        # good  ->  [Rune, Rune, Rune]
        # bad   ->  instead of list of Rune objects, it has number objects { "5": Rune , "6": Rune, "7": Rune}
        # so, using monster_id from request data, if exists in database
        if command == 'BattleRiftOfWorldsRaidResult':
            for wizard_monsters in data_req['user_status_list']:
                if data_resp['wizard_info']['wizard_id'] == wizard_monsters['wizard_id']:
                    data_monsters = wizard_monsters['unit_id_list']
                    break
        else:
            data_monsters = data_req['unit_id_list']

        for temp_monster in data_monsters:
            mon = Monster.objects.filter(id=temp_monster['unit_id'])
            if mon.count() > 0:
                monsters.append(mon.first())

        obj, created = DungeonRun.objects.update_or_create(wizard_id=dungeon['wizard_id'], date=dungeon['date'], defaults=dungeon)
        obj.monsters.set(monsters)
        obj.save()
        logger.debug(f"Successfuly created Battle Dungeon Result for {data_resp['wizard_info']['wizard_name']} (ID: {data_resp['wizard_info']['wizard_id']})")
        return True

    def create(self, request):
        # prepare dictionaries for every command
        wizard = dict()
        rune = dict()
        monster = dict()

        if request.data:
            if request.data['command'] == 'HubUserLogin':
                self.handle_profile_upload(request.data)
            elif request.data['command'] == 'BattleRiftOfWorldsRaidStart':
                self.handle_raid_start_upload(request.data)
            elif request.data['command'] == 'BattleDungeonResult' or request.data['command'] == 'BattleRiftOfWorldsRaidResult':
                if not self.handle_dungeon_run_upload(request.data['response'], request.data['request']):
                    return HttpResponse(f"Unknown stage for Rift Raid Battle (ID: {request.data['request']['battle_key']})", status=status.HTTP_400_BAD_REQUEST)
            return HttpResponse(status=status.HTTP_201_CREATED)
        
        logger.error("Given request was invalid")
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)