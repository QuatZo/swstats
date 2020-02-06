from django.http import HttpResponse

from rest_framework import viewsets, permissions, status

from website.models import Wizard, RuneSet, Rune, MonsterFamily, MonsterBase, MonsterSource, Monster, MonsterRep, MonsterHoh, MonsterFusion, Deck, Building, WizardBuilding, Arena, HomunculusSkill, WizardHomunculus, Guild

import copy
import math
from datetime import datetime

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
                monster_base['family_id'] = MonsterFamily.objects.get(id=int(base['id'][:-2]))
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
                monster_hoh['monster_id'] = MonsterBase.objects.get(id=int(hoh['id']))
                monster_hoh['date_open'] = hoh['date_open']
                monster_hoh['date_close'] = hoh['date_close']
                ########################################

                obj, created = MonsterHoh.objects.update_or_create( monster_id=hoh['id'], defaults=monster_hoh, )
            return HttpResponse(status=status.HTTP_201_CREATED)
        
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

class MonsterFusionUploadViewSet(viewsets.ViewSet):
    def create(self, request):
        if request.data:
            for fusion in request.data:
                monster_fusion = dict()
                ########################################
                # Monster Fusion Model
                monster_fusion['monster_id'] = MonsterBase.objects.get(id=int(fusion['id']))
                monster_fusion['cost'] = fusion['cost']
                ########################################

                obj, created = MonsterFusion.objects.update_or_create( monster_id=fusion['id'], defaults=monster_fusion, )
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

class UploadViewSet(viewsets.ViewSet):
    def create(self, request):
        # prepare dictionaries for every command
        wizard = dict()
        rune = dict()
        monster = dict()

        if request.data:
            if request.data["command"] == "HubUserLogin":
                data = request.data

                print("Checking if guild", data['guild']['guild_info']['guild_id'], "exists...")
                guild = Guild.objects.filter(id=data['guild']['guild_info']['guild_id'])
                guild_uptodate = False
                if guild.exists():
                    print("Guild profile exists... Checking if it's up-to-date...")
                    guild = guild.filter(last_update__gte=datetime.utcfromtimestamp(data['tvalue']))
                    if guild.exists():
                        print("Guild profile is up-to-date.")
                        guild_uptodate = True
                    else:
                        print("Updating guild profile", data['guild']['guild_info']['guild_id'])
                        guild.delete()
                else:
                    print("Guild profile does NOT exists. Starting first-time guild profile upload for", data['guild']['guild_info']['guild_id'])

                if not guild_uptodate:
                    ########################################
                    # Guild Model
                    print("Guild")
                    guild = dict()
                    temp_guild = data['guild']['guild_info']
                    temp_gw_best = data['guildwar_ranking_stat']['best']
                    guild['id'] = temp_guild['guild_id']
                    guild['level'] = temp_guild['level']
                    guild['members_amount'] = temp_guild['member_now']
                    guild['gw_best_place'] = temp_gw_best['rank']
                    guild['gw_best_ranking'] = temp_gw_best['rating_id']
                    guild['last_update'] = datetime.utcfromtimestamp(data['tvalue'])
                    obj, created = Guild.objects.update_or_create( id=guild['id'], defaults=guild, )
                    print("Guild done")
                    ########################################

                print("Checking if profile", data['wizard_info']['wizard_name'], "( ID:", data['wizard_info']['wizard_id'], ") exists...")
                wiz = Wizard.objects.filter(id=data['wizard_info']['wizard_id'])
                wizard_uptodate = False
                if wiz.exists():
                    print("Profile exists... Checking if it's up-to-date...")
                    wizard = wiz.filter(last_update__gte=datetime.utcfromtimestamp(data['tvalue']))
                    if wizard.exists():
                        print("Wizard profile is up-to-date.")
                        wizard_uptodate = True
                    else:
                        print("Updating profile", data['wizard_info']['wizard_name'], "( ID:", data['wizard_info']['wizard_id'], ")")
                        wiz.delete()
                else:
                    print("Profile does NOT exists. Starting first-time profile upload for", data['wizard_info']['wizard_name'], "( ID:", data['wizard_info']['wizard_id'], ")")

                if wizard_uptodate:
                    return HttpResponse(status=status.HTTP_200_OK)

                temp_wizard = data['wizard_info']
                temp_runes = data['runes']
                for monster in data['unit_list']:
                    for rune in monster['runes']:
                        temp_runes.append(rune)
                ########################################
                # Wizard Model
                print("Wizard")
                wizard = dict()
                wizard['id'] = temp_wizard['wizard_id']
                wizard['mana'] = temp_wizard['wizard_mana']
                wizard['crystals'] = temp_wizard['wizard_crystal']
                wizard['crystals_paid'] = temp_wizard['wizard_crystal_paid']
                wizard['last_login'] = temp_wizard['wizard_last_login']
                wizard['country'] = temp_wizard['wizard_last_country']
                wizard['lang'] = temp_wizard['wizard_last_lang']
                wizard['level'] = temp_wizard['wizard_level']
                wizard['energy'] = temp_wizard['wizard_energy']
                wizard['energy_max'] = temp_wizard['energy_max']
                wizard['arena_wing'] = temp_wizard['arena_energy']
                wizard['glory_point'] = temp_wizard['honor_point']
                wizard['guild_point'] = temp_wizard['guild_point']
                wizard['rta_point'] = temp_wizard['honor_medal']
                wizard['rta_mark'] = temp_wizard['honor_mark']
                wizard['event_coin'] = temp_wizard['event_coin']
                wizard['antibot_count'] = data['quiz_reward_info']['reward_count']
                wizard['raid_level'] = data['raid_info_list'][0]['available_stage_id']
                wizard['storage_capacity'] = data['unit_depository_slots']['number']
                wizard['last_update'] = datetime.utcfromtimestamp(data['tvalue'])
                wizard['guild'] = Guild.objects.get(id=guild['id'])
                obj, created = Wizard.objects.update_or_create( id=wizard['id'], defaults=wizard, )
                print("Wizard done")
                ########################################

                print("Runes")
                for temp_rune in temp_runes:
                    rune = dict()
                    ########################################
                    # Rune Model
                    rune['id'] = temp_rune['rune_id']
                    rune['user_id'] = Wizard.objects.get(id=temp_rune['wizard_id'])
                    rune['slot'] = temp_rune['slot_no']
                    rune['quality'] = temp_rune['rank']
                    rune['stars'] = temp_rune['class']
                    rune['rune_set'] = RuneSet.objects.get(id=temp_rune['set_id'])
                    rune['upgrade_curr'] = temp_rune['upgrade_curr']
                    rune['base_value'] = temp_rune['base_value']
                    rune['sell_value'] = temp_rune['sell_value']
                    rune['primary'] = temp_rune['pri_eff'][0]
                    rune['primary_value'] = temp_rune['pri_eff'][1]
                    rune['innate'] = temp_rune['prefix_eff'][0]
                    rune['innate_value'] = temp_rune['prefix_eff'][1]
                    rune['substats'] = [sub[0] for sub in temp_rune['sec_eff']]
                    rune['substats_values'] = [sub[1] for sub in temp_rune['sec_eff']]
                    rune['substats_enchants'] = [sub[2] for sub in temp_rune['sec_eff']]
                    rune['substats_grindstones'] = [sub[3] for sub in temp_rune['sec_eff']]
                    rune['quality_original'] = temp_rune['extra']
                    eff_curr, eff_max = calc_efficiency(temp_rune)
                    rune['efficiency'] = eff_curr
                    rune['efficiency_max'] = eff_max
                    rune['equipped'] = True if temp_rune['occupied_type'] == 1 else False
                    ########################################
                    obj, created = Rune.objects.update_or_create( id=rune['id'], defaults=rune, )
                print("Runes done")

                print("Monsters")
                for temp_monster in data['unit_list']:
                    monster = dict()
                    ########################################
                    # Monster Model
                    monster['id'] = temp_monster['unit_id']
                    monster['user_id'] = Wizard.objects.get(id=temp_monster['wizard_id'])
                    monster['base_monster'] = MonsterBase.objects.get(id=temp_monster['unit_master_id'])
                    monster['level'] = temp_monster['unit_level']
                    monster['stars'] = temp_monster['class']

                    ####################
                    # Stats calc
                    stats = calc_stats(temp_monster, temp_monster['runes'])
                    monster['hp'] = stats['hp']
                    monster['attack'] = stats['attack']
                    monster['defense'] = stats['defense']
                    monster['speed'] = stats['speed']
                    monster['res'] = stats['res']
                    monster['acc'] = stats['acc']
                    monster['crit_rate'] = stats['crit_rate']
                    monster['crit_dmg'] = stats['crit_dmg']
                    ####################
                    monster['skills'] = [skill[1] for skill in temp_monster['skills']]
                   
                    monster_runes = [Rune.objects.get(id=rune['rune_id']) for rune in temp_monster['runes']]
                    # monster['runes'].set(monster_runes)
                    sum_eff = 0
                    for monster_rune in monster_runes:
                        sum_eff += monster_rune.efficiency
                    monster['avg_eff'] = round(sum_eff / len(monster_runes), 2) if len(monster_runes) > 0 else 0.00

                    monster['created'] = temp_monster['create_time']
                    monster['source'] = MonsterSource.objects.get(id=temp_monster['source'])
                    monster['transmog'] = True if temp_monster['costume_master_id'] else False
                    monster['storage'] = True if temp_monster['building_id'] == 5 else False # temporarily building_id = 5 is Storage
                    monster['locked'] = True if temp_monster['unit_id'] in data['unit_lock_list'] else False
                    ########################################
                    obj, created = Monster.objects.update_or_create( id=monster['id'], defaults=monster, )
                    obj.runes.set(monster_runes)
                    obj.save()
                print("Monsters done")


                ########################################
                # Wizard Rep Monster Model
                print("Wizard's rep monsters")
                obj, created = MonsterRep.objects.update_or_create( wizard_id=wizard['id'], defaults={
                    'wizard_id': Wizard.objects.get(id=wizard['id']), 
                    'monster_id': Monster.objects.get(id=temp_wizard['rep_unit_id'])
                }, )
                print("Wizard's rep monsters done")
                ########################################

                ########################################
                # Wizard Deck Model
                print("Wizard's decks")
                for temp_deck in data['deck_list']:
                    deck = dict()
                    deck['wizard_id'] = Wizard.objects.get(id=wizard['id'])
                    deck['place'] = temp_deck['deck_type']
                    deck['number'] = temp_deck['deck_seq']
                    deck['leader'] = Monster.objects.get(id=temp_deck['leader_unit_id'])
                    deck_monsters = monster_runes = [Monster.objects.get(id=monster_id) for monster_id in temp_deck['unit_id_list'] if monster_id]
                    obj, created = Deck.objects.update_or_create( wizard_id=wizard['id'], place=temp_deck['deck_type'], number=temp_deck['deck_seq'], defaults=deck, )
                    obj.monsters.set(deck_monsters)
                    obj.save()
                print("Wizard's decks done")
                ########################################

                ########################################
                # Wizard Building Model
                print("Wizard's buildings")
                for temp_building in Building.objects.all():
                    building = dict()
                    building['wizard_id'] = Wizard.objects.get(id=wizard['id'])
                    building['building_id'] = temp_building
                    building['level'] = 0
                    obj, created = WizardBuilding.objects.get_or_create( wizard_id=building['wizard_id'], building_id=building['building_id'], defaults=building, )

                for deco in data['deco_list']:
                    building = dict()
                    building['wizard_id'] = Wizard.objects.get(id=deco['wizard_id'])
                    building['building_id'] = Building.objects.get(id=deco['master_id'])
                    building['level'] = deco['level']
                    obj, created = WizardBuilding.objects.update_or_create( wizard_id=building['wizard_id'], building_id=building['building_id'], defaults=building, )
                print("Wizard's buildings done")
                ########################################

                ########################################
                # Arena Model
                print("Arena")
                arena = dict()
                arena['wizard_id'] = Wizard.objects.get(id=wizard['id'])
                arena['wins'] = data['pvp_info']['arena_win']
                arena['loses'] = data['pvp_info']['arena_lose']
                arena['rank'] = data['pvp_info']['rating_id']
                for _def in data['defense_unit_list']:
                    arena['def_' + str(_def['pos_id'])] = Monster.objects.get(id=_def['unit_id'])
                obj, created = Arena.objects.update_or_create( wizard_id=wizard['id'], defaults=arena, )
                print("Arena done")
                ########################################

                ########################################
                # Wizard Homunculus Model
                print("Homunculus")
                homunculus = data['homunculus_skill_list']
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
                print("Homunculus done")
                ########################################

            return HttpResponse(status=status.HTTP_201_CREATED)
        
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)