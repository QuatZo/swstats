from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse

from rest_framework import viewsets, permissions, status

from .models import Wizard, RuneSet, Rune, MonsterFamily, MonsterBase, MonsterSource, Monster, MonsterRep
from .serializers import WizardSerializer, RuneSetSerializer, RuneSerializer, MonsterFamilySerializer, MonsterBaseSerializer, MonsterSourceSerializer, MonsterSerializer, MonsterRepSerializer

import copy
import math

# Temporarily here
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
def specific_rune(request, rune_id):
    rune = get_object_or_404(Rune, id=rune_id)
    context = { 'rune': rune, }

    return render( request, 'website/runes/specific.html', context )

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

class UploadViewSet(viewsets.ViewSet):
    def create(self, request):
        # prepare dictionaries for every command
        wizard = dict()
        rune = dict()
        monster = dict()

        if request.data:
            if request.data["command"] == "HubUserLogin":
                data = request.data
                print("Starting profile upload for", data['wizard_info']['wizard_name'], "( ID:", data['wizard_info']['wizard_id'], ")")

                temp_wizard = data['wizard_info']
                temp_runes = data['runes']
                for monster in data['unit_list']:
                    for rune in monster['runes']:
                        temp_runes.append(rune)

                ########################################
                # Wizard Model
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
                ########################################
                obj, created = Wizard.objects.update_or_create( id=wizard['id'], defaults=wizard, )

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
                    rune['equipped'] = temp_rune['occupied_type'] - 1 # needs more testing
                    ########################################
                    obj, created = Rune.objects.update_or_create( id=rune['id'], defaults=rune, )

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
                    monster['avg_eff'] = sum_eff / len(monster_runes) if len(monster_runes) > 0 else 0.00

                    monster['created'] = temp_monster['create_time']
                    monster['storage'] = True if temp_monster['building_id'] == 5 else False # temporarily building_id = 5 is Storage
                    monster['source'] = MonsterSource.objects.get(id=temp_monster['source'])
                    ########################################
                    obj, created = Monster.objects.update_or_create( id=monster['id'], defaults=monster, )
                    obj.runes.set(monster_runes)
                    obj.save()

                ########################################
                # Wizard Rep Monster Model
                obj, created = MonsterRep.objects.update_or_create( wizard_id=wizard['id'], defaults={
                    'wizard_id': Wizard.objects.get(id=wizard['id']), 
                    'monster_id': Monster.objects.get(id=monster['id'])
                }, )
                ########################################

            return HttpResponse(status=status.HTTP_201_CREATED)
        
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)