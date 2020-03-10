from django.http import HttpResponse
from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from django.template.loader import render_to_string

import logging

from website.models import *
from website.serializers import CommandSerializer
from website.exceptions import ProfileDoesNotExist

import copy
import math
import datetime
import json
import statistics
from operator import itemgetter

logger = logging.getLogger(__name__)

def log_request_data(data):
    logger.debug(f"Error/Warning during desktop app data upload occured for request: {json.dumps(data)}")

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
        eff_mean = statistics.mean(efficiencies)
        eff_median = statistics.median(efficiencies)
        eff_st_dev = statistics.stdev(efficiencies)
        maxed = len([True for rune in runes if rune['class'] == 15 ])

        return {
            'all': runes,
            'unequipped': runes_unequipped,
            'equipped': runes_equipped,
            'locked': runes_locked,
            'rta': runes_rta,

            'count': len(runes),
            'unequipped_count': len(runes_unequipped),
            'equipped_count': len(runes_unequipped),
            'locked_count': len(runes_locked),
            
            'eff_min': eff_min,
            'eff_max': eff_max,
            'eff_mean': eff_mean,
            'eff_median': eff_median,
            'eff_st_dev': eff_st_dev,

            'maxed': maxed,
        }
    
    def parse_guild_members(self, guild_members, guild_member_defenses):
        members = list()
        for temp_member in guild_members.keys():
            member = guild_members[temp_member]
            defenses = [row['unit_list'] for row in guild_member_defenses if row['wizard_id'] == member['wizard_id']][0]
            if defenses:
                defense_1 = len(defenses[0])
                defense_2 = len(defenses[1])

            members.append({
                'name': member['wizard_name'],
                'joined': datetime.datetime.utcfromtimestamp(member['join_timestamp']),
                'last_login': datetime.datetime.utcfromtimestamp(member['last_login_timestamp']),
                'defense_1': defense_1,
                'defense_2': defense_2,
            })
        
        return members

    def parse_guild(self, guild, ranking, guild_member_defenses):
        guild_info = guild['guild_info']

        siege_monsters = list()

        return {
            'name': guild_info['name'],
            'master': guild_info['master_wizard_name'],
            'best_ranking': Guild().get_guild_ranking_name(ranking['best']['rating_id']),
            'current_ranking': Guild().get_guild_ranking_name(ranking['current']['rating_id']),
            'members_max': guild_info['member_now'],
            'members_max': guild_info['member_max'],
            'defenses_count': len(guild_member_defenses),
            'defenses_max': guild_info['member_now'] * 2 * 3, # 2 defenses and 3 monsters per defense
            'members': self.parse_guild_members(guild['guild_members'], guild_member_defenses),
        }

    def parse_friends(self, friend_list):
        friends = list()
        
        for friend in friend_list:
            friends.append({
                'name': friend['wizard_name'],
                'last_login': datetime.datetime.utcfromtimestamp(friend['last_login_timestamp']),
                'rep': {
                    'monster': MonsterBase.objects.get(id=friend['rep_unit_master_id']),
                    'level': friend['rep_unit_level'],
                    'stars': friend['rep_unit_class'],
                },
            })


        return friends 

    # check
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

    def create(self, request):
        # upload by using ajax, focused on stuff that Desktop App had
        context = { }

        # temporarily
        if request.is_ajax():
            data = request.data
            if 'command' in data.keys() and data['command'] != 'HubUserLogin':
                context = {'error': "Given File is an invalid Summoners War JSON File."}
            else:
                try: # basically, it's really bad idea to put whole thing in KeyError, need to think about other error handling later
                    runes_equipped = [rune for monster in data['unit_list'] for rune in monster['runes']]
                    context = {
                        'wizard': self.parse_wizard(data['wizard_info'], data['dimension_hole_info']['energy']),
                        'monsters': self.parse_monsters(data['unit_list'], data['unit_lock_list'], data['world_arena_rune_equip_list']),
                        'runes': self.parse_runes(data['runes'], runes_equipped, data['rune_lock_list'], data['world_arena_rune_equip_list']),
                        # 'rta': self.parse_rta(request.data), # not sure if needed
                        # 'dim_hole': self.dimension_hole_calculator(request.data), # not sure if worth
                        # 'buildings': self.something_here(some_arguments),
                        'guild': self.parse_guild(data['guild'], data['guildwar_ranking_stat'], data['guild_member_defense_list']),
                        'friends': self.parse_friends(data['friend_list']),
                    }
                except KeyError:
                    context = {'error': "Given File is an invalid Summoners War JSON File."}
            html = render_to_string('website/desktopapp/desktopapp_content.html', context)
            return HttpResponse(html)

def get_desktop(request):
    """Return the Desktop page."""
    return render( request, 'website/desktopapp/desktopapp_index.html')
 