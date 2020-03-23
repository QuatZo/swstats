from django.http import HttpResponse
from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from django.template.loader import render_to_string

import logging

from website.models import *

import copy
import math
import datetime
import json
import statistics
from operator import itemgetter

logger = logging.getLogger(__name__)

def log_request_data(data):
    logger.debug(f"Error/Warning during desktop app data upload occured for request: {json.dumps(data)}")

def get_arena_towers_cost():
    return {
        'id_4': [ 100, 280, 460, 640, 820, 1000, 1180, 1360, 1540, 1720, ],
        'id_5': [ 40, 90, 140, 190, 240, 290, 340, 390, 440, 490, ],
        'id_6': [ 240, 440, 640, 840, 1040, 1240, 1440, 1640, 1840, 2040, ],
        'id_7': [ 80, 130, 180, 230, 280, 330, 380, 430, 480, 530, ],
        'id_8': [ 200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000, ],
        'id_9': [ 150, 375, 600, 825, 1050, 1275, 1500, 1725, 1950, 2175, ],
        'id_10': [ 20, 80, 140, 200, 260, 320, 380, 440, 500, 560, ],
        'id_11': [ 50, 100, 150, 200, 250, 300, 350, 400, 450, 500, ],
        'id_15': [ 120, 240, 360, 480, 600, 720, 840, 960, 1080, 1200, ],
        'id_16': [ 120, 240, 360, 480, 600, 720, 840, 960, 1080, 1200, ],
        'id_17': [ 120, 240, 360, 480, 600, 720, 840, 960, 1080, 1200, ],
        'id_18': [ 120, 240, 360, 480, 600, 720, 840, 960, 1080, 1200, ],
        'id_19': [ 120, 240, 360, 480, 600, 720, 840, 960, 1080, 1200, ],
        'id_31': [ 120, 240, 360, 480, 600, 720, 840, 960, 1080, 1200, ],
        'id_34': [ 80, 130, 180, 230, 280, 330, 380, 430, 480, 530, ],
        'id_35': [ 30, 80, 130, 180, 230, 280, 330, 380, 430, 480, ],
    }

def get_guild_flags_cost():
    return {
        'id_36': [ 280, 460, 800, 1250, 1810, 2320, 2910, 3590, 4350, 5200, ],
        'id_37': [ 260, 410, 700, 1080, 1560, 1990, 2490, 3070, 3720, 4440, ],
        'id_38': [ 330, 540, 930, 1450, 2100, 2680, 3360, 4140, 5020, 5990, ],
        'id_39': [ 300, 460, 760, 1160, 1670, 2130, 2660, 3270, 3960, 4720, ],
    }
  
def get_siege_rewards():
    return {
        'rank_1011': {
            'crystals': [20, 15, 10], # fixed
            'points': [3, 2, 2], # percentage
        },
        'rank_2011': {
            'crystals': [30, 25, 20], # fixed
            'points': [6, 4, 4], # percentage
        },
        'rank_2012': {
            'crystals': [40, 30, 25], # fixed
            'points': [9, 6, 6], # percentage
        },
        'rank_2013': {
            'crystals': [50, 40, 30], # fixed
            'points': [12, 8, 8], # percentage
        },
        'rank_3011': {
            'crystals': [60, 45, 35], # fixed
            'points': [15, 11, 11], # percentage
        },
        'rank_3012': {
            'crystals': [80, 65, 50], # fixed
            'points': [18, 13, 13], # percentage
        },
        'rank_3013': {
            'crystals': [100, 80, 60], # fixed
            'points': [21, 15, 15], # percentage
        },
        'rank_4011': {
            'crystals': [140, 100, 80], # fixed
            'points': [27, 20, 20], # percentage
        },
        'rank_4012': {
            'crystals': [200, 160, 130], # fixed
            'points': [32, 25, 25], # percentage
        },
        'rank_4013': {
            'crystals': [250, 200, 170], # fixed
            'points': [37, 30, 30], # percentage
        },
    }

def get_guild_war_rewards():
    return {
        'challenger': {
            'battle': 7,
            'war': 20,
        },
        'fighter': {
            'battle': 8,
            'war': 30,
        },
        'conqueror': {
            'battle': 9,
            'war': 40,
        },
        'guardian': {
            'battle': 10,
            'war': 50,
        },
    }

def get_dimhole_axp():
    return [320, 420, 560, 740, 960]

# Create your views here.
class DesktopUploadViewSet(viewsets.ViewSet):
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

    def parse_wizard(self, wizard, dim_hole_energy):
        return {
            'name': wizard['wizard_name'],
            'country': wizard['wizard_last_country'],
            'level': wizard['wizard_level'],
            'mana': wizard['wizard_mana'],
            'crystals': wizard['wizard_crystal'],
            'guild_points': wizard['guild_point'],
            'glory_points': wizard['honor_point'],
            'rta_points': wizard['honor_medal'],
            'shapeshifting_stones': wizard['costume_point'],
            'social_points': wizard['social_point_current'],
            'ancient_coins': wizard['event_coin'],
            'energy': wizard['wizard_energy'],
            'energy_max': wizard['energy_max'],
            'dim_hole_energy': dim_hole_energy,
            'arena_wings': wizard['arena_energy'],
            'dim_rift_crystals': wizard['darkportal_energy'],
        }

    def parse_monsters(self, monsters, locked_monsters, rta_monsters):
        attributes = MonsterBase().get_attributes_as_dict() # monsters[id]['attribute']
        archetypes = MonsterBase().get_types_as_dict() # monsters[id]['unit_master_id'][MonsterBase MODEL]

        monsters_fusion = MonsterFusion.objects.all().prefetch_related('monster')
        monsters_hoh = MonsterHoh.objects.all().prefetch_related('monster')

        base_monsters = list(set([monster['unit_master_id'] for monster in monsters]))
        base_monsters = MonsterBase.objects.filter(id__in=base_monsters).values('id', 'name', 'archetype', 'attribute', 'awaken', 'base_class', 'family').order_by('id').prefetch_related('family')

        base_stars = {
            'star_1': [1, 0],
            'star_2': [2, 0],
            'star_3': [3, 0],
            'star_4': [4, 0],
            'star_5': [5, 0],
        }

        monster_elements = dict()
        monster_archetypes = dict()
        for key, val in attributes.items():
            if val not in monster_elements.keys():
                monster_elements[val] = 0
        for key, val in archetypes.items():
            if val not in monster_archetypes.keys():
                monster_archetypes[val] = 0

        nat5_non_fusion = list()
        ld_nat4plus_non_fusion_nor_hoh = list()
        for monster in monsters:
            base_monster = base_monsters.get(id=monster['unit_master_id'])
            monster_elements[attributes[monster['attribute']]] += 1
            monster_archetypes[archetypes[base_monster['archetype']]] += 1
            base_stars['star_' + str(base_monster['base_class'])][1] += 1
            if base_monster['base_class'] == 5:
                if not monsters_fusion.filter(monster=base_monster['id']).exists():
                    nat5_non_fusion.append({
                        'monster': base_monster['name'],
                        'acquiration_date': monster['create_time'],
                    })
            if monster['attribute'] >= 4 and base_monster['base_class'] >= 4: # l&d, 4*+
                if not monsters_hoh.filter(monster=base_monster['id']).exists() and not monsters_fusion.filter(monster=base_monster['id']).exists():
                    ld_nat4plus_non_fusion_nor_hoh.append({
                        'monster': base_monster['name'],
                        'acquiration_date': monster['create_time'],
                    })

        last_nat5 = sorted(nat5_non_fusion, key=itemgetter('acquiration_date'), reverse = True)[0]
        last_nat4_ld = sorted(ld_nat4plus_non_fusion_nor_hoh, key=itemgetter('acquiration_date'), reverse = True)[0]

        return {
            'all': monsters,
            'locked': locked_monsters,
            'rta': rta_monsters,

            'count': len(monsters),
            'elements': monster_elements,
            'archetypes': monster_archetypes,
            'base_class': base_stars,

            'nat5_not_fusion': nat5_non_fusion,
            'last_nat5': (datetime.datetime.today() - datetime.datetime.strptime(last_nat5['acquiration_date'], "%Y-%m-%d %H:%M:%S")).days,

            'ld4plus_not_fusion': ld_nat4plus_non_fusion_nor_hoh,
            'last_ld4plus': (datetime.datetime.today() - datetime.datetime.strptime(last_nat4_ld['acquiration_date'], "%Y-%m-%d %H:%M:%S")).days,
        }

    def parse_runes(self, runes_unequipped, runes_equipped, runes_locked, runes_rta):
        runes = [*runes_unequipped, *runes_equipped] # unpack both and create one list

        efficiencies = [self.calc_efficiency(rune)[0] for rune in runes] # only current efficiency
        eff_min = min(efficiencies)
        eff_max = max(efficiencies)
        eff_mean = round(statistics.mean(efficiencies), 2)
        eff_median = round(statistics.median(efficiencies), 2)
        eff_st_dev = round(statistics.stdev(efficiencies), 2)
        maxed = len([True for rune in runes if rune['upgrade_curr'] == 15 ])

        runes_len = len(runes)
        runes_unequipped_len = len(runes_unequipped)
        runes_equipped_len = len(runes_equipped)
        runes_locked_len = len(runes_locked)

        sets = {row['id']:[row['name'].lower(), 0] for row in RuneSet.objects.values('id', 'name') if row['id'] != 99} # all sets except immemorial
        slots = {
            'slot_1': [1, 0],
            'slot_2': [2, 0],
            'slot_3': [3, 0],
            'slot_4': [4, 0],
            'slot_5': [5, 0],
            'slot_6': [6, 0],
        }

        for rune in runes:
            sets[rune['set_id']][1] += 1
            slots['slot_' + str(rune['slot_no'])][1] += 1

        return {
            'all': runes,
            'unequipped': runes_unequipped,
            'equipped': runes_equipped,
            'locked': runes_locked,
            'rta': runes_rta,

            'count': runes_len,
            'unequipped_count': runes_unequipped_len,
            'unequipped_percentage': round(runes_unequipped_len * 100 / runes_len, 2),
            'equipped_count': runes_equipped_len,
            'equipped_percentage': round(runes_equipped_len * 100 / runes_len, 2),
            'locked_count': runes_locked_len,
            'locked_percentage': round(runes_locked_len * 100 / runes_len, 2),
            
            'eff_min': eff_min,
            'eff_max': eff_max,
            'eff_mean': eff_mean,
            'eff_median': eff_median,
            'eff_st_dev': eff_st_dev,

            'maxed': maxed,
            'maxed_percentage': round(maxed * 100 / runes_len, 2),

            'sets': sets,
            'slots': slots,
        }
    
    def parse_guild_members(self, guild_members, guild_member_defenses):
        members = list()
        for temp_member in guild_members.keys():
            member = guild_members[temp_member]
            defenses = [row['unit_list'] for row in guild_member_defenses if row['wizard_id'] == member['wizard_id']][0]
            if defenses:
                defense_1 = len(defenses[0])
                defense_2 = len(defenses[1])

            last_login =  datetime.datetime.utcfromtimestamp(member['last_login_timestamp'])
            members.append({
                'name': member['wizard_name'],
                'joined': datetime.datetime.utcfromtimestamp(member['join_timestamp']),
                'last_login': last_login,
                'last_login_days': (datetime.datetime.today() - last_login).days,
                'defense_1': defense_1,
                'defense_2': defense_2,
            })
        
            members = sorted(members, key=itemgetter('last_login'), reverse = True)
        return members

    def parse_guild(self, guild, ranking, guild_member_defenses):
        guild_info = guild['guild_info']

        siege_monsters = list()

        gw_members_count = len(guild_member_defenses)
        gw_members_defense_count = 0
        for wizard in guild_member_defenses:
            for defense in wizard['unit_list']:
                gw_members_defense_count += len(defense)

        return {
            'name': guild_info['name'],
            'master': guild_info['master_wizard_name'],
            'best_ranking': Guild().get_guild_ranking_name(ranking['best']['rating_id']),
            'current_ranking': Guild().get_guild_ranking_name(ranking['current']['rating_id']),
            'members_count': guild_info['member_now'],
            'members_max': guild_info['member_max'],
            'members_gw': gw_members_count,
            'defenses_count': gw_members_defense_count,
            'defenses_max': gw_members_count * 2 * 3, # 2 defenses and 3 monsters per defense
            'members': self.parse_guild_members(guild['guild_members'], guild_member_defenses),
        }

    def parse_friends(self, friend_list):
        friends = list()

        for friend in friend_list:
            last_login = datetime.datetime.utcfromtimestamp(friend['last_login_timestamp'])
            friends.append({
                'name': friend['wizard_name'],
                'last_login': last_login,
                'last_login_days': (datetime.datetime.today() - last_login).days,
                'rep': {
                    'monster': MonsterBase.objects.get(id=friend['rep_unit_master_id']),
                    'level': friend['rep_unit_level'],
                    'stars': friend['rep_unit_class'],
                },
            })

        friends = sorted(friends, key=itemgetter('last_login'), reverse = True)

        return friends 

    def create(self, request):
        # upload by using ajax, focused on stuff that Desktop App had
        context = { }

        if request.is_ajax():
            data = request.data
            if 'command' in data.keys() and data['command'] != 'HubUserLogin':
                context = {'error': "Given File is an invalid Summoners War JSON File."}
            else:
                try: # basically, it's really bad idea to put whole thing in KeyError, need to think about other error handling later
                    runes_equipped = [rune for monster in data['unit_list'] for rune in monster['runes']]
                    context = {
                        'date': datetime.datetime.utcfromtimestamp(data['tvalue']).strftime("%Y-%m-%d %H:%M:%S"),
                        'wizard': self.parse_wizard(data['wizard_info'], data['dimension_hole_info']['energy']),
                        'monsters': self.parse_monsters(data['unit_list'], data['unit_lock_list'], data['world_arena_rune_equip_list']),
                        'runes': self.parse_runes(data['runes'], runes_equipped, data['rune_lock_list'], data['world_arena_rune_equip_list']),
                        # 'rta': self.parse_rta(request.data), # not sure if needed
                        'guild': self.parse_guild(data['guild'], data['guildwar_ranking_stat'], data['guild_member_defense_list']),
                        'friends': self.parse_friends(data['friend_list']),
                    }
                except KeyError as e:
                    if 'world_arena_rune_equip_list' in str(e):
                        context = {'error': "Given JSON File is before Separate Rune Management Update, please update your JSON profile."}
                    else:
                        context = {'error': "Given File is an invalid Summoners War JSON File."}
                        logger.debug(e)
            html = render_to_string('website/desktopapp/desktopapp_content.html', context)
            return HttpResponse(html)

def get_desktop(request):
    """Return the Desktop page."""
    return render( request, 'website/desktopapp/desktopapp_index.html')
 
def get_buildings_calculator(request):
    buildings_cost = get_arena_towers_cost()
    buildings_cost.update(get_guild_flags_cost())
    siege_rewards = get_siege_rewards()
    gw_rewards = get_guild_war_rewards()

    buildings = Building.objects.all()

    context = {
        'buildings_cost': buildings_cost,
        'buildings': buildings,

        'siege': siege_rewards,
        'gw': gw_rewards,
    }

    return render( request, 'website/desktopapp/buildings_index.html', context)

def get_dimhole_calculator(request):
    monsters = dict(MonsterBase.objects.values_list('id', 'name'))

    context = {
        'monsters': monsters,
        'axp_per_level': json.dumps(get_dimhole_axp()),
    }

    return render( request, 'website/desktopapp/dimholecalc_index.html', context)