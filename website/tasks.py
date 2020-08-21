from celery import shared_task 
from django.urls import reverse
from django.shortcuts import get_object_or_404

from .models import *
from .functions import *

import requests
import logging
import datetime
import pickle
import time
import itertools
import math
from operator import itemgetter

logger = logging.getLogger(__name__)


########################## UPLOAD #########################
@shared_task
def handle_profile_upload_task(data):
    try:
        profile_guild = True
        if data['guild']['guild_info'] is None:
            logger.debug(f"Profile {data['wizard_info']['wizard_id']} has no guild.")
            profile_guild = False
        else:
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

        if profile_guild and not guild_uptodate:
            parse_guild(data['guild']['guild_info'], data['guildwar_ranking_stat']['best'], data['tvalue'])

        logger.debug(f"Checking if profile {data['wizard_info']['wizard_id']} exists...")
        wiz = Wizard.objects.filter(id=data['wizard_info']['wizard_id'])
        wizard_uptodate = False
        if wiz.exists():
            logger.debug(f"Profile {data['wizard_info']['wizard_id']} exists... Checking if it's up-to-date...")
            wizard = wiz.filter(last_update__gte=datetime.datetime.utcfromtimestamp(data['tvalue']))
            if wizard.exists():
                logger.debug(f"Wizard profile {data['wizard_info']['wizard_id']} is up-to-date")
                wizard_uptodate = True
            else:
                logger.debug(f"Updating profile {data['wizard_info']['wizard_id']}")
        else:
            logger.debug(f"Profile {data['wizard_info']['wizard_id']} does NOT exists. Starting first-time profile upload")

        if wizard_uptodate:
            return

        temp_wizard = data['wizard_info']

        temp_runes = data['runes']
        has_artifacts = False
        temp_artifacts = list()
        if 'artifacts' in data.keys():
            has_artifacts = True
            temp_artifacts = data['artifacts']
        for monster in data['unit_list']:
            for rune in monster['runes']:
                temp_runes.append(rune)
            if has_artifacts:
                for artifact in monster['artifacts']:
                    temp_artifacts.append(artifact)

        ########################################
        # Wizard Model
        wizard = parse_wizard(temp_wizard, data['tvalue'])
        try:
            wizard['antibot_count'] = data['quiz_reward_info']['reward_count']
            wizard['raid_level'] = data['raid_info_list'][0]['available_stage_id']
            wizard['storage_capacity'] = data['unit_depository_slots']['number']
        except KeyError:
            logger.info("[Wizard]: No info about anti bot feature, raid level nor storage capacity")
        
        if profile_guild:
            wizard_guilds = Guild.objects.filter(id=data['guild']['guild_info']['guild_id'])
            if wizard_guilds.count() > 0:
                wizard['guild'] = wizard_guilds.first()
        else:
            wizard['guild'] = None
        obj, created = Wizard.objects.update_or_create( id=wizard['id'], defaults=wizard, )
        ########################################

        for temp_rune in temp_runes:
            parse_rune(temp_rune, data['rune_lock_list'])

        for temp_artifact in temp_artifacts:
            parse_artifact(temp_artifact)

        for temp_monster in data['unit_list']:
            parse_monster(temp_monster, data['building_list'], data['unit_lock_list'])

        if 'world_arena_rune_equip_list' in data.keys():
            parse_runes_rta(data['world_arena_rune_equip_list'])
        else:
            logger.warning("Given JSON file is before an RTA Rune Management Update!")
            log_request_data(request.data)

        # monster rep
        obj, created = MonsterRep.objects.update_or_create( wizard__id=wizard['id'], defaults={
            'wizard': Wizard.objects.get(id=wizard['id']), 
            'monster': Monster.objects.get(id=temp_wizard['rep_unit_id'])
        }, )

        parse_decks(data['deck_list'], wizard['id'])
        parse_wizard_buildings(data['deco_list'], wizard['id'])
        parse_arena_records(data['pvp_info'], data['defense_unit_list'], wizard['id'])
        parse_wizard_homunculus(data['homunculus_skill_list'])

        logger.debug(f"Fully uploaded profile for {data['wizard_info']['wizard_id']}")
    except Exception as e: # to find all exceptions and fix them without breaking the whole app, it is a temporary solution
        log_exception(e, data=data)

@shared_task
def handle_friend_upload_task(data):
    try:
        temp_wizard = data['friend']
        if 'wizard_id' not in temp_wizard.keys():
            if len(temp_wizard['unit_list']):
                wizard_id = temp_wizard['unit_list'][0]['wizard_id']
            else:
                logger.debug(f"[Friend Upload] No Wizard ID. Ending...")
                return
        else:
            wizard_id = temp_wizard['wizard_id']
        logger.debug(f"[Friend Upload] Checking if profile {wizard_id} exists...")
        # don't overwrite complete data with incomplete
        if Wizard.objects.filter(id=wizard_id).exists():
            logger.debug(f"[Friend Upload] Profile {wizard_id} exists... Ending... ")
            return

        logger.debug(f"[Friend Upload] Profile {wizard_id} does NOT exists. Starting first-time profile upload")
        wizard = parse_wizard(temp_wizard, data['tvalue'])
        wizard['id'] = wizard_id
        obj, created = Wizard.objects.update_or_create( id=wizard['id'], defaults=wizard, )

        for temp_monster in temp_wizard['unit_list']:
            good = True
            for rune in temp_monster['runes']:
                if type(rune) is str:
                    good = False
                    break
                parse_rune(rune)
            for artifact in temp_monster['artifacts']:
                parse_artifact(artifact)
            if good:
                parse_monster(temp_monster, temp_wizard['building_list'], )

        parse_wizard_buildings(temp_wizard['deco_list'], wizard['id'])

        logger.debug(f"[Friend Upload] Fully uploaded profile for {wizard_id}")
    except Exception as e: # to find all exceptions and fix them without breaking the whole app, it is a temporary solution
        log_exception(e, data=data)

@shared_task
def handle_monster_recommendation_upload_task(data_resp, data_req):
    try:
        monsters = MonsterBase.objects.filter(id=data_req['unit_master_id'])
        if monsters.count():
            votes = monsters.first().recommendation_votes

            monster = dict()
            for monster_rec in data_resp['comments']['top']:
                if not has_banned_words(monster_rec['comment']) and votes < monster_rec['recommend_count']:
                    monster['recommendation_text'] = monster_rec['comment']
                    monster['recommendation_votes'] = monster_rec['recommend_count']
                    obj, created = MonsterBase.objects.update_or_create(id=data_req['unit_master_id'], defaults=monster)
    except Exception as e: # to find all exceptions and fix them without breaking the whole app, it is a temporary solution
        log_exception(e, data_resp=data_resp, data_req=data_req)

@shared_task
def handle_raid_start_upload_task(data_resp, data_req):
    try:
        dungeon = dict()

        dungeon['battle_key'] = data_req['battle_key']
        dungeon['stage'] = data_resp['battle_info']['room_info']['stage_id']
        dungeon['date'] = datetime.datetime.utcfromtimestamp(data_resp['tvalue'])
        wizard, created = Wizard.objects.update_or_create(id=data_req['wizard_id'], defaults=parse_wizard(data_resp['wizard_info'], data_resp['tvalue']))
        dungeon['wizard'] = Wizard.objects.get(id=data_req['wizard_id'])

        unit_list = None
        for user in data_resp['battle_info']['user_list']:
            if user['wizard_id'] == data_req['wizard_id']:
                for temp_monster in user['deck_list']:
                    mon = Monster.objects.filter(id=temp_monster['unit_info']['unit_id'])
                    if mon.count() > 0:
                        temp_monster_instance = mon.first()
                        dungeon['monster_' + str(temp_monster['index'])] = temp_monster_instance
                        if temp_monster['leader']:
                            dungeon['leader'] = temp_monster_instance

        obj, created = RaidDungeonRun.objects.update_or_create(battle_key=dungeon['battle_key'], defaults=dungeon)
        logger.debug(f"Successfully created Rift of Worlds (R{dungeon['stage']}) Start for {data_req['wizard_id']}")
    except Exception as e: # to find all exceptions and fix them without breaking the whole app, it is a temporary solution
        log_exception(e, data_resp=data_resp, data_req=data_req)

@shared_task
def handle_raid_run_upload_task(data_resp, data_req):
    try:
        dungeon = dict()
        if data_req['win_lose'] == 1:
            dungeon['win'] = True
            time_str = str(data_req['clear_time'])
            _time = {
                'hour': 0 if int(time_str[:-3]) < 3600 else math.floor(int(time_str[:-3]) / 3600),
                'minute': 0 if int(time_str[:-3]) < 60 else math.floor(int(time_str[:-3]) / 60),
                'second': int(time_str[:-3]) if int(time_str[:-3]) < 60 else int(time_str[:-3]) % 60,
                'microsecond': int(time_str[-3:]) * 1000,
            }
            dungeon['clear_time'] = datetime.time(_time['hour'], _time['minute'], _time['second'], _time['microsecond'])
        else:
            dungeon['win'] = False
        
        obj, created = RaidDungeonRun.objects.update_or_create(battle_key=data_req['battle_key'], defaults=dungeon)
        logger.debug(f"Successfully created Rift of Worlds Run for {data_req['wizard_id']}")
    except Exception as e: # to find all exceptions and fix them without breaking the whole app, it is a temporary solution
        log_exception(e, data_resp=data_resp, data_req=data_req)

@shared_task
def handle_dungeon_run_upload_task(data_resp, data_req):
    try:
        command = data_resp['command']
        logger.debug(f"Starting Battle Dungeon Result upload for {data_resp['wizard_info']['wizard_id']}")
        dungeon = dict()
        wizard, created = Wizard.objects.update_or_create(id=data_resp['wizard_info']['wizard_id'], defaults=parse_wizard(data_resp['wizard_info'], data_resp['tvalue']))
        dungeon['wizard'] = Wizard.objects.get(id=data_resp['wizard_info']['wizard_id'])
        dungeon['dungeon'] = data_req['dungeon_id']
        dungeon['stage'] = data_req['stage_id']
        dungeon['date'] = datetime.datetime.utcfromtimestamp(data_resp['tvalue'])
        
        if data_resp['win_lose'] == 1:
            dungeon['win'] = True
            time_str = str(data_resp['clear_time']['current_time'])
            _time = {
                'hour': 0 if int(time_str[:-3]) < 3600 else math.floor(int(time_str[:-3]) / 3600),
                'minute': 0 if int(time_str[:-3]) < 60 else math.floor(int(time_str[:-3]) / 60),
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
        data_monsters = data_req['unit_id_list']

        for temp_monster in data_monsters:
            mon = Monster.objects.filter(id=temp_monster['unit_id'])
            if mon.count() > 0:
                monsters.append(mon.first())

        obj, created = DungeonRun.objects.update_or_create(wizard=dungeon['wizard'], date=dungeon['date'], defaults=dungeon)
        obj.monsters.set(monsters)
        obj.save()
        logger.debug(f"Successfuly created Battle Dungeon ({dungeon['dungeon']}) Result for {data_resp['wizard_info']['wizard_id']}")
    except Exception as e: # to find all exceptions and fix them without breaking the whole app, it is a temporary solution
        log_exception(e, data_resp=data_resp, data_req=data_req)

@shared_task
def handle_rift_dungeon_start_upload_task(data_resp, data_req):
    try:
        dungeon = dict()

        dungeon['battle_key'] = data_resp['battle_key']
        dungeon['dungeon'] = data_req['dungeon_id']
        dungeon['date'] = datetime.datetime.utcfromtimestamp(data_resp['tvalue'])
        wizard, created = Wizard.objects.update_or_create(id=data_resp['wizard_info']['wizard_id'], defaults=parse_wizard(data_resp['wizard_info'], data_resp['tvalue']))
        dungeon['wizard'] = Wizard.objects.get(id=data_resp['wizard_info']['wizard_id'])

        for temp_monster in data_req['unit_id_list']:
            mon = Monster.objects.filter(id=temp_monster['unit_id'])
            if mon.count() > 0:
                temp_monster_instance = mon.first()
                dungeon['monster_' + str(temp_monster['slot_index'])] = temp_monster_instance
                if data_req['leader_index'] == temp_monster['slot_index']:
                    dungeon['leader'] = temp_monster_instance

        obj, created = RiftDungeonRun.objects.update_or_create(battle_key=dungeon['battle_key'], defaults=dungeon)
        obj.save()
        logger.debug(f"Successfuly created Rift Dungeon ({dungeon['dungeon']}) Start for {data_resp['wizard_info']['wizard_id']}")
    except Exception as e: # to find all exceptions and fix them without breaking the whole app, it is a temporary solution
        log_exception(e, data_resp=data_resp, data_req=data_req)

@shared_task
def handle_rift_dungeon_run_upload_task(data_resp, data_req):
    try:
        dungeon = dict()
        if data_req['battle_result'] == 1:
            dungeon['win'] = True
            time_str = str(data_req['clear_time'])
            _time = {
                'hour': 0 if int(time_str[:-3]) < 3600 else math.floor(int(time_str[:-3]) / 3600),
                'minute': 0 if int(time_str[:-3]) < 60 else math.floor(int(time_str[:-3]) / 60),
                'second': int(time_str[:-3]) if int(time_str[:-3]) < 60 else int(time_str[:-3]) % 60,
                'microsecond': int(time_str[-3:]) * 1000,
            }
            dungeon['clear_time'] = datetime.time(_time['hour'], _time['minute'], _time['second'], _time['microsecond'])
        else:
            dungeon['win'] = False
        dungeon['clear_rating'] = data_resp['rift_dungeon_box_id']
        
        # need to check if always table like this
        dmg_records = data_req['round_list']
        dungeon['dmg_phase_1'] = dmg_records[0][1]
        if len(dmg_records) > 1:
            dungeon['dmg_phase_glory'] = dmg_records[1][1]
        if len(dmg_records) > 2:
            dungeon['dmg_phase_2'] = dmg_records[2][1]

        obj, created = RiftDungeonRun.objects.update_or_create(battle_key=data_req['battle_key'], defaults=dungeon)
        logger.debug(f"Successfuly created Rift Dungeon Result (ID: {data_req['battle_key']})")
    except Exception as e: # to find all exceptions and fix them without breaking the whole app, it is a temporary solution
        log_exception(e, data_resp=data_resp, data_req=data_req)

@shared_task
def handle_siege_defenses_upload_task(data):
    try:
        defenses = list()
        temp_mons = dict()

        wizards = Wizard.objects.all().values()

        for deck in data['defense_deck_list']:
            wizard = [wiz for wiz in wizards if wiz['id'] == data['wizard_info_list'][0]['wizard_id']]
            if not wizard:
                continue
            temp_mons[deck['deck_id']] = list()
            defenses.append({
                'id': deck['deck_id'],
                'win': deck['win_count'],
                'lose': deck['lose_count'],
                'ratio': deck['winning_rate'],
                'wizard': Wizard.objects.get(id=wizard[0]['id']),
                'last_update': datetime.datetime.utcfromtimestamp(data['tvalue']),
            })
        
        for deck_units in data['defense_unit_list']:
            if 'unit_info' in deck_units.keys():
                for defense in defenses:
                    if defense['id'] == deck_units['deck_id'] and len(temp_mons[deck_units['deck_id']]) < 3:
                        monster = Monster.objects.filter(id=deck_units['unit_info']['unit_id'])
                        monster_first = monster.first()
                        if monster.exists():
                            temp_mons[deck_units['deck_id']].append(monster_first)
                            if deck_units['pos_id'] == 1:
                                defense['leader'] = monster_first
        
        for defense in defenses:
            obj, created = SiegeRecord.objects.update_or_create(id=defense['id'], defaults=defense)
            obj.monsters.set(temp_mons[defense['id']])
            guild = Guild.objects.filter(id=data['wizard_info_list'][0]['guild_id'])
            if guild.exists():
                defense['wizard'].guild = guild.first()
                defense['wizard'].save()
            obj.save()
        logger.debug(f"Fully uploaded Siege Defenses")
    except Exception as e: # to find all exceptions and fix them without breaking the whole app, it is a temporary solution
        log_exception(e, data=data)

@shared_task
def handle_siege_ranking_upload_task(data):
    try:
        Guild.objects.filter(id=data['guildsiege_stat_info']['curr']['guild_id']).update(siege_ranking=data['guildsiege_stat_info']['curr']['rating_id'])
    except Exception as e: # to find all exceptions and fix them without breaking the whole app, it is a temporary solution
        log_exception(e, data=data)

@shared_task
def handle_dimension_hole_run_upload_task(data_resp, data_req):
    try:
        command = data_resp['command']
        logger.debug(f"Starting Dimension Hole Run upload for {data_resp['wizard_info']['wizard_id']}")
        dungeon = dict()
        wizard, created = Wizard.objects.update_or_create(id=data_resp['wizard_info']['wizard_id'], defaults=parse_wizard(data_resp['wizard_info'], data_resp['tvalue']))
        dungeon['id'] = data_req['battle_key']
        dungeon['wizard'] = Wizard.objects.get(id=data_resp['wizard_info']['wizard_id'])
        dungeon['dungeon'] = data_resp['dungeon_id']
        dungeon['stage'] = data_resp['difficulty']
        dungeon['date'] = datetime.datetime.utcfromtimestamp(data_resp['tvalue'])
        dungeon['practice'] = data_resp['practice_mode']


        if data_resp['win_lose'] == 1:
            dungeon['win'] = True
            time_str = str(data_resp['clear_time']['current_time'])
            _time = {
                'hour': 0 if int(time_str[:-3]) < 3600 else math.floor(int(time_str[:-3]) / 3600),
                'minute': 0 if int(time_str[:-3]) < 60 else math.floor(int(time_str[:-3]) / 60),
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
        data_monsters = data_req['unit_id_list']
        for temp_monster in data_monsters:
            mon = Monster.objects.filter(id=temp_monster['unit_id'])
            if mon.count() > 0:
                monsters.append(mon.first())

        obj, created = DimensionHoleRun.objects.update_or_create(id=data_req['battle_key'], defaults=dungeon)
        obj.monsters.set(monsters)
        obj.save()
        logger.debug(f"Successfuly created Dimension Hole ({dungeon['dungeon']}) Run for {data_resp['wizard_info']['wizard_id']}")
    except Exception as e: # to find all exceptions and fix them without breaking the whole app, it is a temporary solution
        log_exception(e, data_resp=data_resp, data_req=data_req)

@shared_task
def handle_wizard_arena_upload_task(data_resp, data_req):
    try:
        if data_req['wizard_id'] == data_req['target_wizard_id'] or data_resp['lobby_wizard_log']['page_no'] != 1:
            return
        wizard = {
            'id': data_req['target_wizard_id'],
            'last_update': datetime.datetime.utcfromtimestamp(data_resp['tvalue']),
        }
        Wizard.objects.update_or_create(id=wizard['id'], defaults=wizard, )
        arena_rank = {
            'wizard': Wizard.objects.get(id=wizard['id']),
            'rank': data_resp['lobby_wizard_log']['pvp_best_rating_id'],
        }
        Arena.objects.update_or_create(wizard=arena_rank['wizard'], defaults=arena_rank, )
    except Exception as e:
        log_exception(e, data_resp=data_resp, data_req=data_req)

########################### WEB ###########################
# region RUNES
@shared_task
def get_runes_task(request_get):
    runes = Rune.objects.order_by('-efficiency')

    is_filter = False 
    filters = list()

    if request_get:
        is_filter = True

    if 'set' in request_get.keys() and request_get['set'] and request_get['set'][0] != '0':
        filters.append('Set: ' + request_get['set'][0])
        runes = runes.filter(rune_set__name=request_get['set'][0])

    if 'slot' in request_get.keys() and request_get['slot'] and request_get['slot'][0] != '0':
        try:
            slot = int(request_get['slot'][0])
        except ValueError:
            slot = 0
        filters.append('Slot: ' + str(slot))
        runes = runes.filter(slot=slot)
    
    if 'quality' in request_get.keys() and request_get['quality'] and request_get['quality'][0] != '0':
        filters.append('Quality: ' + request_get['quality'][0])
        quality_id = Rune().get_rune_quality_id(request_get['quality'][0])
        runes = runes.filter(quality=quality_id)
    
    if 'quality_original' in request_get.keys() and request_get['quality_original'] and request_get['quality_original'][0] != '0':
        filters.append('Original Quality: ' + request_get['quality_original'][0])
        quality_original_id = Rune().get_rune_quality_id(request_get['quality_original'][0])
        runes = runes.filter(quality_original=quality_original_id)

    if 'main_stat' in request_get.keys() and request_get['main_stat'] and request_get['main_stat'][0] != '0':
        main_stat = request_get['main_stat'][0].replace('plus', '+').replace('percent', '%')
        filters.append('Main Stat: ' + main_stat)
        main_stat_id = Rune().get_rune_primary_id(main_stat)
        runes = runes.filter(primary=main_stat_id)
    
    if 'stars' in request_get.keys() and request_get['stars'] and request_get['stars'][0] != '0':
        try:
            stars = int(request_get['stars'][0]) % 10
        except ValueError:
            stars = 0
        filters.append('Stars: ' + str(stars))
        runes = runes.filter(Q(stars=stars) | Q(stars=stars + 10)) # since ancient runes have 11-16

    if 'eff_min' in request_get.keys() and request_get['eff_min'][0] and request_get['eff_min'][0] != '0':
        filters.append('Efficiency Minimum: ' + request_get['eff_min'][0])
        runes = runes.filter(efficiency__gte=request_get['eff_min'][0])

    if 'eff_max' in request_get.keys() and request_get['eff_max'][0] and request_get['eff_max'][0] != '0':
        filters.append('Efficiency Maximum: ' + request_get['eff_max'][0])
        runes = runes.filter(efficiency__lte=request_get['eff_max'][0])

    runes_count = runes.count()
    
    normal_distribution_runes = get_rune_list_normal_distribution(runes, 40, runes_count)
    
    runes_by_set = get_rune_list_grouped_by_set(runes)
    runes_by_slot = get_rune_list_grouped_by_slot(runes)
    runes_by_quality = get_rune_list_grouped_by_quality(runes)
    runes_by_quality_original = get_rune_list_grouped_by_quality_original(runes)
    runes_by_main_stat = get_rune_list_grouped_by_main_stat(runes)
    runes_by_stars = get_rune_list_grouped_by_stars(runes)

    best_runes = get_rune_list_best(runes, 100, runes_count)
    fastest_runes = get_rune_list_fastest(runes, 100, runes_count)
    best_runes_ids = [rune.id for rune in best_runes]
    fastest_runes_ids = [rune.id for rune in fastest_runes]

    filter_options = {
        'sets': list(RuneSet.objects.all().values_list('name', flat=True)),
        'slots': [1, 2, 3, 4, 5, 6],
        'qualities':  Rune().get_rune_qualities(),
        'main_stats': Rune().get_rune_effects(),
        'stars': [1, 2 , 3, 4, 5, 6],
    }
    
    context = {
        # filters
        'is_filter': is_filter,
        'filters': '[' + ', '.join(filters) + ']',
        'filter_options': filter_options,
        'request': request_get,

        # chart distribution
        'all_distribution': normal_distribution_runes['distribution'],
        'all_means': normal_distribution_runes['scope'],
        'all_color': create_rgb_colors(normal_distribution_runes['interval']),

        # chart group by set
        'set_name': runes_by_set['name'],
        'set_count': runes_by_set['quantity'],
        'set_color': create_rgb_colors(runes_by_set['length']),

        # chart group by slot
        'slot_number': runes_by_slot['number'],
        'slot_count': runes_by_slot['quantity'],
        'slot_color': create_rgb_colors(runes_by_slot['length']),

        # chart group by quality
        'quality_name': runes_by_quality['name'],
        'quality_count': runes_by_quality['quantity'],
        'quality_color': create_rgb_colors(runes_by_quality['length']),

        # chart group by original quality
        'quality_original_name': runes_by_quality_original['name'],
        'quality_original_count': runes_by_quality_original['quantity'],
        'quality_original_color': create_rgb_colors(runes_by_quality_original['length']),

        # chart group by main stat
        'main_stat_name': runes_by_main_stat['name'],
        'main_stat_count': runes_by_main_stat['quantity'],
        'main_stat_color': create_rgb_colors(runes_by_main_stat['length']),

        # chart group by stars
        'stars_number': runes_by_stars['number'],
        'stars_count': runes_by_stars['quantity'],
        'stars_color': create_rgb_colors(runes_by_stars['length']),

        # table best by efficiency
        'best_runes_ids': best_runes_ids,
        'best_amount': len(best_runes),

        # table best by speed
        'fastest_runes_ids': fastest_runes_ids,
        'fastest_amount': len(fastest_runes),
    }

    return context

@shared_task
def get_rune_by_id_task(request_get, arg_id):
    rune = get_object_or_404(Rune.objects.prefetch_related('rune_set', 'equipped_runes', 'equipped_runes__base_monster', 'equipped_runes__runes', 'equipped_runes__runes__rune_set' ), id=arg_id)
    runes = Rune.objects.filter(slot=rune.slot, rune_set=rune.rune_set, primary=rune.primary)

    try:
        rta_monster_id = RuneRTA.objects.filter(rune=rune.id).prefetch_related('monster', 'monster__base_monster', 'rune', 'rune__rune_set').first().monster.id
    except AttributeError:
        rta_monster_id = None

    similar_ids = get_rune_similar(runes, rune)

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
    runes_cols = ['id', 'slot', 'rune_set__id', 'primary', 'efficiency',
        'sub_hp_sum', 'sub_hp_flat_sum', 'sub_atk_sum', 'sub_atk_flat_sum', 'sub_def_sum', 'sub_def_flat_sum', 'sub_speed_sum',
        'sub_res_sum', 'sub_acc_sum', 'sub_crit_rate_sum', 'sub_crit_dmg_sum']
    df_runes = pd.DataFrame(runes.values_list(*runes_cols), columns=[runes_col.replace('_sum', '') for runes_col in runes_cols]).drop_duplicates(subset=['id']).fillna(0)
    df_means = df_runes.mean()
    rune_temp = {
        'hp_flat': sum(rune.sub_hp_flat) if rune.sub_hp_flat is not None else 0,
        'hp': sum(rune.sub_hp) if rune.sub_hp is not None else 0,
        'atk_flat': sum(rune.sub_atk_flat) if rune.sub_atk_flat is not None else 0,
        'atk': sum(rune.sub_atk) if rune.sub_atk is not None else 0,
        'def_flat': sum(rune.sub_def_flat) if rune.sub_def_flat is not None else 0,
        'def': sum(rune.sub_def) if rune.sub_def is not None else 0,
        'speed': sum(rune.sub_speed) if rune.sub_speed is not None else 0,
        'acc': sum(rune.sub_acc) if rune.sub_acc is not None else 0,
        'res': sum(rune.sub_res) if rune.sub_res is not None else 0,
        'crit_rate': sum(rune.sub_crit_rate) if rune.sub_crit_rate is not None else 0,
        'crit_dmg': sum(rune.sub_crit_dmg) if rune.sub_crit_dmg is not None else 0,
    }
    ranks = calc_rune_comparison_stats(rune.id, rune_temp['hp_flat'], rune_temp['hp'], rune_temp['atk_flat'], rune_temp['atk'], rune_temp['def_flat'], rune_temp['def'], rune_temp['speed'], rune_temp['res'], rune_temp['acc'], rune_temp['crit_rate'], rune_temp['crit_dmg'], rune.efficiency, df_runes, len(df_runes), df_means)['rank']

    context = {
        'rta_monster_id': rta_monster_id,
        'ranks': ranks,
        'similar_ids': similar_ids,
        'arg_id': arg_id,
    }

    return context
# endregion

# region ARTIFACTS
@shared_task
def get_artifacts_task(request_get):
    artifacts = Artifact.objects.order_by('-efficiency')

    is_filter = False 
    filters = list()

    if request_get:
        is_filter = True

    if 'rtype' in request_get.keys() and request_get['rtype'] and request_get['rtype'][0] != '0':
        filters.append('Type: ' + request_get['rtype'][0])
        rtype_id = Artifact().get_artifact_rtype_id(request_get['rtype'][0])
        artifacts = artifacts.filter(rtype=rtype_id)

    if 'primary' in request_get.keys() and request_get['primary'] and request_get['primary'][0] != '0':
        primary = request_get['primary'][0].replace('plus', '+').replace('percent', '%')
        filters.append('Primary: ' + primary)
        primary_id = Artifact().get_artifact_primary_id(primary)
        artifacts = artifacts.filter(primary=primary_id)
    
    if 'quality' in request_get.keys() and request_get['quality'] and request_get['quality'][0] != '0':
        filters.append('Quality: ' + request_get['quality'][0])
        quality_id = Artifact().get_artifact_quality_id(request_get['quality'][0])
        artifacts = artifacts.filter(quality=quality_id)
    
    if 'quality_original' in request_get.keys() and request_get['quality_original'] and request_get['quality_original'][0] != '0':
        filters.append('Original Quality: ' + request_get['quality_original'][0])
        quality_original_id = Artifact().get_artifact_quality_id(request_get['quality_original'][0])
        artifacts = artifacts.filter(quality_original=quality_original_id)

    if 'attribute' in request_get.keys() and request_get['attribute'] and request_get['attribute'][0] != '0':
        filters.append('Element: ' + request_get['attribute'][0])
        attribute_id = Artifact().get_artifact_attribute_id(request_get['attribute'][0])
        artifacts = artifacts.filter(attribute=attribute_id)

    if 'archetype' in request_get.keys() and request_get['archetype'] and request_get['archetype'][0] != '0':
        filters.append('Archetype: ' + request_get['archetype'][0])
        archetype_id = Artifact().get_artifact_archetype_id(request_get['archetype'][0])
        artifacts = artifacts.filter(archetype=archetype_id)
    
    if 'eff_min' in request_get.keys() and request_get['eff_min'][0] and request_get['eff_min'][0] != '0':
        filters.append('Efficiency Minimum: ' + request_get['eff_min'][0])
        artifacts = artifacts.filter(efficiency__gte=request_get['eff_min'][0])

    if 'eff_max' in request_get.keys() and request_get['eff_max'][0] and request_get['eff_max'][0] != '0':
        filters.append('Efficiency Maximum: ' + request_get['eff_max'][0])
        artifacts = artifacts.filter(efficiency__lte=request_get['eff_max'][0])

    artifacts_count = artifacts.count()
    
    normal_distribution_artifacts = get_rune_list_normal_distribution(artifacts, min(40, artifacts_count), artifacts_count)
    
    artifacts_by_rtype = get_artifact_list_grouped_by_rtype(artifacts)
    artifacts_by_primary = get_artifact_list_grouped_by_primary(artifacts)
    artifacts_by_quality = get_artifact_list_grouped_by_quality(artifacts)
    artifacts_by_quality_original = get_artifact_list_grouped_by_quality_original(artifacts)
    artifacts_by_attribute = get_artifact_list_grouped_by_attribute(artifacts)
    artifacts_by_archetype = get_artifact_list_grouped_by_archetype(artifacts)

    best_artifacts = get_rune_list_best(artifacts, 100, artifacts_count)
    best_artifacts_ids = [artifact.id for artifact in best_artifacts]
    
    filter_options = {
        'qualities': Artifact().get_artifact_qualities(),
        'archetypes': Artifact().get_artifact_archetypes(),
        'attributes': Artifact().get_artifact_attributes(),
        'main_stats': Artifact().get_artifact_main_stats(),
    }

    context = {
        # filters
        'is_filter': is_filter,
        'filters': '[' + ', '.join(filters) + ']',
        'filter_options': filter_options,
        'request': request_get,

        # chart distribution
        'all_distribution': normal_distribution_artifacts['distribution'],
        'all_means': normal_distribution_artifacts['scope'],
        'all_color': create_rgb_colors(normal_distribution_artifacts['interval']),

        # chart group by rtype
        'rtype_name': artifacts_by_rtype['name'],
        'rtype_count': artifacts_by_rtype['quantity'],
        'rtype_color': create_rgb_colors(artifacts_by_rtype['length']),

        # chart group by primary
        'primary_name': artifacts_by_primary['name'],
        'primary_count': artifacts_by_primary['quantity'],
        'primary_color': create_rgb_colors(artifacts_by_primary['length']),

        # chart group by quality
        'quality_name': artifacts_by_quality['name'],
        'quality_count': artifacts_by_quality['quantity'],
        'quality_color': create_rgb_colors(artifacts_by_quality['length']),

        # chart group by original quality
        'quality_original_name': artifacts_by_quality_original['name'],
        'quality_original_count': artifacts_by_quality_original['quantity'],
        'quality_original_color': create_rgb_colors(artifacts_by_quality_original['length']),
        
        # chart group by attribute
        'attribute_name': artifacts_by_attribute['name'],
        'attribute_count': artifacts_by_attribute['quantity'],
        'attribute_color': create_rgb_colors(artifacts_by_attribute['length']),
        
        # chart group by archetype
        'archetype_name': artifacts_by_archetype['name'],
        'archetype_count': artifacts_by_archetype['quantity'],
        'archetype_color': create_rgb_colors(artifacts_by_archetype['length']),

        # table best by efficiency
        'best_artifacts_ids': best_artifacts_ids,
        'best_amount': len(best_artifacts),
    }

    return context

@shared_task
def get_artifact_by_id_task(request_get, arg_id):
    artifact = get_object_or_404(Artifact.objects.prefetch_related('equipped_artifacts'), id=arg_id)
    artifacts = Artifact.objects.all()

    similar_ids = get_artifact_similar(artifacts, artifact)

    context = {
        'similar_ids': similar_ids,
        'arg_id': arg_id,
    }

    return context
# endregion

# region MONSTERS
@shared_task
def get_monsters_task(request_get):
    monsters = Monster.objects.order_by('-avg_eff')
    is_filter = False 
    filters = list()

    if request_get:
        is_filter = True

    if 'family' in request_get.keys() and request_get['family'] and request_get['family'][0] != '0':
        family = request_get['family'][0].replace('_', ' ')
        filters.append('Family: ' + family)
        monsters = monsters.filter(base_monster__family__name=family)
    
    if 'attribute' in request_get.keys() and request_get['attribute'] and request_get['attribute'][0] != '0':
        filters.append('Element: ' + request_get['attribute'][0])
        monsters = monsters.filter(base_monster__attribute=MonsterBase().get_attribute_id(request_get['attribute'][0]))
    
    if 'archetype' in request_get.keys() and request_get['archetype'] and request_get['archetype'][0] != '0':
        filters.append('Archetype: ' + request_get['archetype'][0])
        monsters = monsters.filter(base_monster__archetype=MonsterBase().get_archetype_id(request_get['archetype'][0]))
    
    if 'stars' in request_get.keys() and request_get['stars'][0] and request_get['stars'][0] != '0':
        filters.append('Stars: ' + request_get['stars'][0])
        monsters = monsters.filter(stars=request_get['stars'][0])
    
    if 'base_class' in request_get.keys() and request_get['base_class'][0] and request_get['base_class'][0] != '0':
        filters.append('Natural Stars: ' + request_get['base_class'][0])
        monsters = monsters.filter(base_monster__base_class=request_get['base_class'][0])
    
    if 'eff_min' in request_get.keys() and request_get['eff_min'][0] and request_get['eff_min'][0] != '0':
        filters.append('Efficiency Minimum: ' + request_get['eff_min'][0])
        monsters = monsters.filter(avg_eff_total__gte=request_get['eff_min'][0])
    
    if 'eff_max' in request_get.keys() and request_get['eff_max'][0] and request_get['eff_max'][0] != '0':
        filters.append('Efficiency Maximum: ' + request_get['eff_max'][0])
        monsters = monsters.filter(avg_eff_total__lte=request_get['eff_max'][0])
    
    if 'hp_min' in request_get.keys() and request_get['hp_min'][0] and request_get['hp_min'][0] != '0':
        filters.append('HP Minimum: ' + request_get['hp_min'][0])
        monsters = monsters.filter(hp__gte=request_get['hp_min'][0])
    
    if 'hp_max' in request_get.keys() and request_get['hp_max'][0] and request_get['hp_max'][0] != '0':
        filters.append('HP Maximum: ' + request_get['hp_max'][0])
        monsters = monsters.filter(hp__lte=request_get['hp_max'][0])
    
    if 'atk_min' in request_get.keys() and request_get['atk_min'][0] and request_get['atk_min'][0] != '0':
        filters.append('Attack Minimum: ' + request_get['atk_min'][0])
        monsters = monsters.filter(attack__gte=request_get['atk_min'][0])
    
    if 'atk_max' in request_get.keys() and request_get['atk_max'][0] and request_get['atk_max'][0] != '0':
        filters.append('Attack Maximum: ' + request_get['atk_max'][0])
        monsters = monsters.filter(attack__lte=request_get['atk_max'][0])
    
    if 'def_min' in request_get.keys() and request_get['def_min'][0] and request_get['def_min'][0] != '0':
        filters.append('Defense Minimum: ' + request_get['def_min'][0])
        monsters = monsters.filter(defense__gte=request_get['def_min'][0])
    
    if 'def_max' in request_get.keys() and request_get['def_max'][0] and request_get['def_max'][0] != '0':
        filters.append('Defense Maximum: ' + request_get['def_max'][0])
        monsters = monsters.filter(defense__lte=request_get['def_max'][0])
    
    if 'spd_min' in request_get.keys() and request_get['spd_min'][0] and request_get['spd_min'][0] != '0':
        filters.append('Speed Minimum: ' + request_get['spd_min'][0])
        monsters = monsters.filter(speed__gte=request_get['spd_min'][0])
    
    if 'spd_max' in request_get.keys() and request_get['spd_max'][0] and request_get['spd_max'][0] != '0':
        filters.append('Speed Maximum: ' + request_get['spd_max'][0])
        monsters = monsters.filter(speed__lte=request_get['spd_max'][0])
    
    if 'res_min' in request_get.keys() and request_get['res_min'][0] and request_get['res_min'][0] != '0':
        filters.append('Resistance Minimum: ' + request_get['res_min'][0])
        monsters = monsters.filter(res__gte=request_get['res_min'][0])
    
    if 'res_max' in request_get.keys() and request_get['res_max'][0] and request_get['res_max'][0] != '0':
        filters.append('Resistance Maximum: ' + request_get['res_max'][0])
        monsters = monsters.filter(res__lte=request_get['res_max'][0])
    
    if 'acc_min' in request_get.keys() and request_get['acc_min'][0] and request_get['acc_min'][0] != '0':
        filters.append('Accuracy Minimum: ' + request_get['acc_min'][0])
        monsters = monsters.filter(acc__gte=request_get['acc_min'][0])
    
    if 'acc_max' in request_get.keys() and request_get['acc_max'][0] and request_get['acc_max'][0] != '0':
        filters.append('Accuracy Maximum: ' + request_get['acc_max'][0])
        monsters = monsters.filter(acc__lte=request_get['acc_max'][0])
    
    if 'crit_rate_min' in request_get.keys() and request_get['crit_rate_min'][0] and request_get['crit_rate_min'][0] != '0':
        filters.append('Critical Rate Minimum: ' + request_get['crit_rate_min'][0])
        monsters = monsters.filter(crit_rate__gte=request_get['crit_rate_min'][0])
    
    if 'crit_rate_max' in request_get.keys() and request_get['crit_rate_max'][0] and request_get['crit_rate_max'][0] != '0':
        filters.append('Critical Rate Maximum: ' + request_get['crit_rate_max'][0])
        monsters = monsters.filter(crit_rate__lte=request_get['crit_rate_max'][0])
    
    if 'crit_dmg_min' in request_get.keys() and request_get['crit_dmg_min'][0] and request_get['crit_dmg_min'][0] != '0':
        filters.append('Critical Damage Minimum: ' + request_get['crit_dmg_min'][0])
        monsters = monsters.filter(crit_dmg__gte=request_get['crit_dmg_min'][0])
    
    if 'crit_dmg_max' in request_get.keys() and request_get['crit_dmg_max'][0] and request_get['crit_dmg_max'][0] != '0':
        filters.append('Critical Damage Maximum: ' + request_get['crit_dmg_max'][0])
        monsters = monsters.filter(crit_dmg__lte=request_get['crit_dmg_max'][0])
    
    if 'eff_hp_min' in request_get.keys() and request_get['eff_hp_min'][0] and request_get['eff_hp_min'][0] != '0':
        filters.append('Effective HP Minimum: ' + request_get['eff_hp_min'][0])
        monsters = monsters.filter(eff_hp__gte=request_get['eff_hp_min'][0])
    
    if 'eff_hp_max' in request_get.keys() and request_get['eff_hp_max'][0] and request_get['eff_hp_max'][0] != '0':
        filters.append('Effective HP Maximum: ' + request_get['eff_hp_max'][0])
        monsters = monsters.filter(eff_hp__lte=request_get['eff_hp_max'][0])
    
    if 'eff_hp_def_min' in request_get.keys() and request_get['eff_hp_def_min'][0] and request_get['eff_hp_def_min'][0] != '0':
        filters.append('E. HP Def Break Minimum: ' + request_get['eff_hp_def_min'][0])
        monsters = monsters.filter(eff_hp_def_break__gte=request_get['eff_hp_def_min'][0])
    
    if 'eff_hp_def_max' in request_get.keys() and request_get['eff_hp_def_max'][0] and request_get['eff_hp_def_max'][0] != '0':
        filters.append('E. HP Def Break Maximum: ' + request_get['eff_hp_def_max'][0])
        monsters = monsters.filter(eff_hp_def_break__lte=request_get['eff_hp_def_max'][0])
    
    if 'storage' in request_get.keys() and request_get['storage'][0] and request_get['storage'][0] != '0':
        filters.append('Storage: ' + request_get['storage'][0])
        monsters = monsters.filter(storage=request_get['storage'][0])
    
    if 'hoh' in request_get.keys() and request_get['hoh'][0] and request_get['hoh'][0] != '0':
        filters.append('HoH: ' + request_get['hoh'][0])
        if request_get['hoh'][0] == "True":
            monsters = monsters.filter(base_monster__in=get_monsters_hoh())
        else:
            monsters = monsters.exclude(base_monster__in=get_monsters_hoh())
    
    if 'fusion' in request_get.keys() and request_get['fusion'][0] and request_get['fusion'][0] != '0':
        filters.append('Fusion: ' + request_get['fusion'][0])
        if request_get['fusion'][0] == "True":
            monsters = monsters.filter(base_monster__in=get_monsters_fusion())
        else:
            monsters = monsters.exclude(base_monster__in=get_monsters_fusion())
    
    monsters_count = monsters.count()

    monsters_over_time = get_monster_list_over_time(monsters)
    monsters_by_family = get_monster_list_group_by_family(monsters)
    monsters_by_attribute = get_monster_list_group_by_attribute(monsters)
    monsters_by_type = get_monster_list_group_by_type(monsters)
    monsters_by_base_class = get_monster_list_group_by_base_class(monsters)
    monsters_by_storage = get_monster_list_group_by_storage(monsters)
    monsters_by_hoh = get_monster_list_group_by_hoh(monsters)
    monsters_by_fusion = get_monster_list_group_by_fusion(monsters)
    
    best_monsters_ids = [monster.id for monster in get_monster_list_best(monsters, 50, monsters_count)]
    fastest_monsters_ids = [monster.id for monster in get_monster_list_fastest(monsters, 50, monsters_count)]

    filter_options = {
        'families': list(MonsterFamily.objects.all().values_list('name', flat=True)),
        'elements': MonsterBase().get_monster_attributes(),
        'archetypes': MonsterBase().get_monster_archetypes(),
        'stars': [1, 2, 3, 4, 5, 6],
        'stars_natural': [1, 2, 3, 4, 5, 6],
    }

    context = {
        # filters
        'is_filter': is_filter,
        'filters': '[' + ', '.join(filters) + ']',
        'filter_options': filter_options,
        'request': request_get,

        # chart monster by acquiration date
        'time_timeline': monsters_over_time['time'],
        'time_count': monsters_over_time['quantity'],

        # chart monster by family
        'family_name': monsters_by_family['name'],
        'family_count': monsters_by_family['quantity'],
        'family_color': create_rgb_colors(monsters_by_family['length']),

        # chart monster by attribute
        'attribute_name': monsters_by_attribute['name'],
        'attribute_count': monsters_by_attribute['quantity'],
        'attribute_color': create_rgb_colors(monsters_by_attribute['length']),

        # chart monster by type (archetype)
        'type_name': monsters_by_type['name'],
        'type_count': monsters_by_type['quantity'],
        'type_color': create_rgb_colors(monsters_by_type['length']),

        # chart monster by base class
        'base_class_number': monsters_by_base_class['number'],
        'base_class_count': monsters_by_base_class['quantity'],
        'base_class_color': create_rgb_colors(monsters_by_base_class['length']),

        # chart monster by storage
        'storage_value': monsters_by_storage['value'],
        'storage_count': monsters_by_storage['quantity'],
        'storage_color': create_rgb_colors(monsters_by_storage['length']),

        # chart monster by hoh
        'hoh_value': monsters_by_hoh['value'],
        'hoh_count': monsters_by_hoh['quantity'],
        'hoh_color': create_rgb_colors(monsters_by_hoh['length']),

        # chart monster by fusion
        'fusion_value': monsters_by_fusion['value'],
        'fusion_count': monsters_by_fusion['quantity'],
        'fusion_color': create_rgb_colors(monsters_by_fusion['length']),

        # table best by efficiency
        'best_monsters_ids': best_monsters_ids,
        'best_amount': len(best_monsters_ids),

        # table best by speed
        'fastest_monsters_ids': fastest_monsters_ids,
        'fastest_amount': len(fastest_monsters_ids),
    }

    return context

@shared_task
def get_monster_by_id_task(request_get, arg_id):
    monster = get_object_or_404(Monster.objects.prefetch_related('runes', 'runes__rune_set', 'base_monster', 'runes__equipped_runes', 'runes__equipped_runes__base_monster', 'siege_defense_monsters'), id=arg_id)
    monsters = Monster.objects.filter(base_monster=monster.base_monster)
    
    MAX_COUNT = 50
    rta_runes = list(RuneRTA.objects.filter(monster=monster).values_list('rune__id', flat=True))

    mon_similar_builds = list(monsters.filter(base_monster__attribute=monster.base_monster.attribute, base_monster__family=monster.base_monster.family).exclude(id=monster.id).values_list('id', flat=True))
    mon_similar_builds = random.sample(mon_similar_builds, min(MAX_COUNT, len(mon_similar_builds)))

    rta_similar_builds = list(set(list(RuneRTA.objects.filter(monster__base_monster=monster.base_monster).exclude(monster=monster.id).values_list('monster__id', flat=True))))
    rta_similar_builds = random.sample(rta_similar_builds, min(MAX_COUNT, len(rta_similar_builds)))
    
    monsters_cols = ['id', 'hp', 'attack', 'defense', 'speed', 'res', 'acc', 'crit_rate', 'crit_dmg', 'avg_eff_total', 'eff_hp', 'eff_hp_def_break']
    df_monsters = pd.DataFrame(monsters.values_list(*monsters_cols), columns=monsters_cols).drop_duplicates(subset=['id'])
    
    df_means = df_monsters.mean()
    
    ranks = calc_monster_comparison_stats(monster.id, monster.hp, monster.attack, monster.defense, monster.speed, monster.res, monster.acc, monster.crit_rate, monster.crit_dmg, monster.avg_eff_total, monster.eff_hp, monster.eff_hp_def_break, df_monsters, len(df_monsters), df_means)['rank']

    context = {
        'ranks': ranks,
        'rta_runes': rta_runes,
        'similar_ids': mon_similar_builds,
        'rta_similar_ids': rta_similar_builds,
    }

    return context
# endregion

# region DECKS
@shared_task
def get_decks_task(request_get):
    decks = Deck.objects.all().order_by('-team_runes_eff')
    is_filter = False
    filters = list()

    if request_get:
        is_filter = True

    if 'family' in request_get.keys() and request_get['family']:
        family = request_get['family'][0].replace('_', ' ')
        filters.append('Family: ' + family)
        decks = decks.filter(monsters__base_monster__family__name=family)

    if 'place' in request_get.keys() and request_get['place']:
        place = request_get['place'][0].replace('_', ' ')
        filters.append('Place: ' + place)
        decks = decks.filter(place=Deck().get_place_id(place))
    
    decks = decks.prefetch_related('monsters', 'monsters__base_monster', 'monsters__base_monster__family', 'leader', 'leader__base_monster', 'leader__base_monster__family')
    decks_by_family = get_deck_list_group_by_family(decks)
    decks_by_place = get_deck_list_group_by_place(decks)
    decks_eff = get_deck_list_avg_eff(decks)

    # needs to be last, because it's for TOP table
    amount = min(100, decks.count())
    decks_ids = [deck.id for deck in decks.order_by('-team_runes_eff')[:amount]]

    context = { 
        # filters
        'is_filter': is_filter,
        'filters': '[' + ', '.join(filters) + ']',
        
        # chart group by family members
        'family_name': decks_by_family['name'],
        'family_count': decks_by_family['quantity'],
        'family_color': create_rgb_colors(decks_by_family['length']),

        # chart group by place
        'place_name': decks_by_place['name'],
        'place_count': decks_by_place['quantity'],
        'place_color': create_rgb_colors(decks_by_place['length']),

        # chart best
        'avg_eff_above_decks': decks_eff['above'],
        'avg_eff_above_quantity': len(decks_eff['above']),
        'avg_eff_below_decks': decks_eff['below'],
        'avg_eff_below_quantity': len(decks_eff['below']),
        'avg_eff': round(decks_eff['avg'], 2),

        # Table TOP decks
        'decks_ids': decks_ids,
        'amount': amount,
    }

    return context

@shared_task
def get_deck_by_id_task(request_get):
    return
# endregion

# region DUNGEONS
@shared_task
def get_dungeon_by_stage_task(request_get, name, stage):
    is_filter = False
    filters = list()
    names = name.split('-')

    for i in range(len(names)):
        if names[i] != "of":
            names[i] = names[i].capitalize()
    name = ' '.join(names)

    dungeon_runs = DungeonRun.objects.filter(dungeon=DungeonRun().get_dungeon_id(name), stage=stage).order_by('clear_time')

    if request_get:
        is_filter = True

    if 'base' in request_get.keys() and request_get['base'][0] and request_get['base'][0] != '0':
        base = request_get['base'][0].replace('_', ' ')
        filters.append('Monster: ' + base)
        dungeon_runs_ids = dungeon_runs.filter(monsters__base_monster__name=base).values_list('id', flat=True)
        dungeon_runs = dungeon_runs.filter(id__in=dungeon_runs_ids)
        
    if 'secs_min' in request_get.keys() and request_get['secs_min'][0] and request_get['secs_min'][0] != '0':
        filters.append('Faster than: ' + request_get['secs_min'][0] + ' seconds')
        dungeon_runs = dungeon_runs.filter(clear_time__lte=datetime.timedelta(seconds=int(request_get['secs_min'][0])))

    success_rate_min = 0
    if 'success_rate_min' in request_get.keys() and request_get['success_rate_min'][0] and request_get['success_rate_min'][0] != '0':
        filters.append('Success Rate Minimum: ' + request_get['success_rate_min'][0])
        success_rate_min = float(request_get['success_rate_min'][0])

    success_rate_max = 0
    if 'success_rate_max' in request_get.keys() and request_get['success_rate_max'][0] and request_get['success_rate_max'][0] != '0':
        filters.append('Success Rate Maximum: ' + request_get['success_rate_max'][0])
        success_rate_max = float(request_get['success_rate_max'][0])
        
    dungeon_runs_clear = dungeon_runs.exclude(clear_time__isnull=True).prefetch_related('monsters', 'monsters__base_monster')
    runs_distribution = get_dungeon_runs_distribution(dungeon_runs_clear, 20)
    avg_time = dungeon_runs_clear.aggregate(avg_time=Avg('clear_time'))['avg_time']

    dungeon_runs = dungeon_runs.prefetch_related('monsters')
    
    comps = list()
    for _, group in itertools.groupby(list(dungeon_runs.values('id', 'dungeon', 'monsters__id')), lambda item: item["id"]):
        results = [mon['monsters__id'] for mon in group if mon['monsters__id']]
        if not len(results):
            continue
        results.sort()
        if results and results not in comps and len(results) == 5:
            comps.append(results)    

    try:
        fastest_run = dungeon_runs_clear.order_by('clear_time').first().clear_time.total_seconds()
    except AttributeError:
        fastest_run = None

    records_personal = sorted(get_dungeon_runs_by_comp(comps, dungeon_runs, fastest_run, success_rate_min, success_rate_max), key=itemgetter('sorting_val'), reverse = True)
    base_names, base_quantities = get_dungeon_runs_by_base_class(dungeon_runs_clear)

    context = {
        # filters
        'is_filter': is_filter,
        'filters': '[' + ', '.join(filters) + ']',
        'request': request_get,

        # all
        'name': name,
        'stage': stage,
        'avg_time': str(avg_time),
        
        # chart distribution
        'runs_distribution': runs_distribution['distribution'],
        'runs_means': runs_distribution['scope'],
        'runs_colors': create_rgb_colors(runs_distribution['interval']),

        # chart base
        'base_names': base_names,
        'base_quantity': base_quantities,
        'base_colors': create_rgb_colors(len(base_names)),

        # personal table
        'records_personal': records_personal,
    }

    return context

@shared_task
def get_raid_dungeon_by_stage_task(request_get, stage):
    is_filter = False
    filters = list()

    name = 'Rift of Worlds'

    dungeon_runs = RaidDungeonRun.objects.filter(stage=stage)
    dungeon_runs = dungeon_runs.exclude(monster_1__isnull=True, monster_2__isnull=True, monster_3__isnull=True, monster_4__isnull=True, monster_5__isnull=True, monster_6__isnull=True, monster_7__isnull=True, monster_8__isnull=True, leader__isnull=True)
  
    if request_get:
        is_filter = True

    if 'base' in request_get.keys() and request_get['base'][0] and request_get['base'][0] != '0':
        base = request_get['base'][0].replace('_', ' ')
        filters.append('Monster: ' + base)
        dungeon_runs_final_ids = list()
        for i in range(1, 9):
            dungeon_runs_ids = dungeon_runs.filter(**{f'monster_{i}__base_monster__name': base}).values_list('battle_key', flat=True)
            if dungeon_runs_ids:
                dungeon_runs_final_ids += list(dungeon_runs_ids)
        dungeon_runs = dungeon_runs.filter(battle_key__in=dungeon_runs_final_ids)
        
    if 'secs_min' in request_get.keys() and request_get['secs_min'][0] and request_get['secs_min'][0] != '0':
        filters.append('Faster than: ' + request_get['secs_min'][0] + ' seconds')
        dungeon_runs = dungeon_runs.filter(clear_time__lte=datetime.timedelta(seconds=int(request_get['secs_min'][0])))

    success_rate_min = 0
    if 'success_rate_min' in request_get.keys() and request_get['success_rate_min'][0] and request_get['success_rate_min'][0] != '0':
        filters.append('Success Rate Minimum: ' + request_get['success_rate_min'][0])
        success_rate_min = float(request_get['success_rate_min'][0])

    success_rate_max = 0
    if 'success_rate_max' in request_get.keys() and request_get['success_rate_max'][0] and request_get['success_rate_max'][0] != '0':
        filters.append('Success Rate Maximum: ' + request_get['success_rate_max'][0])
        success_rate_max = float(request_get['success_rate_max'][0])
    
    dungeon_runs = dungeon_runs.prefetch_related('monster_1', 'monster_1__base_monster','monster_2', 'monster_2__base_monster','monster_3', 'monster_3__base_monster','monster_4', 'monster_4__base_monster','monster_5', 'monster_5__base_monster','monster_6', 'monster_6__base_monster','monster_7', 'monster_7__base_monster','monster_8', 'monster_8__base_monster','leader', 'leader__base_monster')
    dungeon_runs_clear = dungeon_runs.exclude(clear_time__isnull=True)
    
    runs_distribution = get_dungeon_runs_distribution(dungeon_runs_clear, 20)
    avg_time = dungeon_runs_clear.aggregate(avg_time=Avg('clear_time'))['avg_time']

    try:
        fastest_run = dungeon_runs_clear.order_by('clear_time').first().clear_time.total_seconds()
    except AttributeError:
        fastest_run = None

    records_personal = sorted(get_raid_dungeon_records_personal(dungeon_runs, fastest_run, success_rate_min, success_rate_max), key=itemgetter('sorting_val'), reverse = True)
    base_names, base_quantities = get_raid_dungeon_runs_by_base_class(dungeon_runs)

    context = {
        # filters
        'is_filter': is_filter,
        'filters': '[' + ', '.join(filters) + ']',
        'request': request_get,
    
        # all
        'name': name,
        'stage': 1,
        'avg_time': str(avg_time),
        
        # chart distribution
        'runs_distribution': runs_distribution['distribution'],
        'runs_means': runs_distribution['scope'],
        'runs_colors': create_rgb_colors(runs_distribution['interval']),
    
        # chart base
        'base_names': base_names,
        'base_quantity': base_quantities,
        'base_colors': create_rgb_colors(len(base_names)),
    
        # personal table
        'records_personal': records_personal,
    }

    return context

@shared_task
def get_rift_dungeon_by_stage_task(request_get, name):
    is_filter = False
    filters = list()
    names = name.split('-')

    for i in range(len(names)):
        if names[i] != "of":
            names[i] = names[i].capitalize()
    name = ' '.join(names)

    dungeon_runs = RiftDungeonRun.objects.filter(dungeon=RiftDungeonRun().get_dungeon_id(name)).exclude(clear_rating=None)
    dungeon_runs = dungeon_runs.exclude(monster_1__isnull=True, monster_2__isnull=True, monster_3__isnull=True, monster_4__isnull=True, monster_5__isnull=True, monster_6__isnull=True, monster_7__isnull=True, monster_8__isnull=True, leader__isnull=True)

    if request_get:
        is_filter = True

    if 'base' in request_get.keys() and request_get['base'][0] and request_get['base'][0] != '0':
        base = request_get['base'][0].replace('_', ' ')
        filters.append('Monster: ' + base)
        dungeon_runs_final_ids = list()
        for i in range(1, 9):
            dungeon_runs_ids = dungeon_runs.filter(**{f'monster_{i}__base_monster__name': base}).values_list('battle_key', flat=True)
            if dungeon_runs_ids:
                dungeon_runs_final_ids += list(dungeon_runs_ids)
        dungeon_runs = dungeon_runs.filter(battle_key__in=dungeon_runs_final_ids)
    
    if 'dmg_min' in request_get.keys() and request_get['dmg_min'][0] and request_get['dmg_min'][0] != '0':
        filters.append('Damage Minimum: ' + request_get['dmg_min'][0])
        dungeon_runs = dungeon_runs.filter(dmg_total__gte=request_get['dmg_min'][0])

    success_rate_min = 0
    if 'success_rate_min' in request_get.keys() and request_get['success_rate_min'][0] and request_get['success_rate_min'][0] != '0':
        filters.append('Success Rate Minimum: ' + request_get['success_rate_min'][0])
        success_rate_min = float(request_get['success_rate_min'][0])

    success_rate_max = 0
    if 'success_rate_max' in request_get.keys() and request_get['success_rate_max'][0] and request_get['success_rate_max'][0] != '0':
        filters.append('Success Rate Maximum: ' + request_get['success_rate_max'][0])
        success_rate_max = float(request_get['success_rate_max'][0])

    dungeon_runs = dungeon_runs.prefetch_related('monster_1', 'monster_1__base_monster','monster_2', 'monster_2__base_monster','monster_3', 'monster_3__base_monster','monster_4', 'monster_4__base_monster','monster_5', 'monster_5__base_monster','monster_6', 'monster_6__base_monster','monster_7', 'monster_7__base_monster','monster_8', 'monster_8__base_monster','leader', 'leader__base_monster')
    dungeon_runs_clear = dungeon_runs.exclude(clear_time__isnull=True)
    
    damage_distribution = get_rift_dungeon_damage_distribution(dungeon_runs, 20)
    avg_time = dungeon_runs_clear.aggregate(avg_time=Avg('clear_time'))['avg_time']


    try:
        highest_damage = dungeon_runs.order_by('-dmg_total').first().dmg_total
    except AttributeError:
        highest_damage = None

    records_personal = sorted(get_rift_dungeon_records_personal(dungeon_runs, highest_damage, success_rate_min, success_rate_max), key=itemgetter('sorting_val'), reverse = True)
    base_names, base_quantities = get_rift_dungeon_runs_by_base_class(dungeon_runs)

    context = {
        # filters
        'is_filter': is_filter,
        'filters': '[' + ', '.join(filters) + ']',
        'request': request_get,
    
        # all
        'name': name,
        'stage': 1,
        'avg_time': str(avg_time),
        
        # chart distribution
        'damage_distribution': damage_distribution['distribution'],
        'damage_means': damage_distribution['scope'],
        'damage_colors': create_rgb_colors(damage_distribution['interval']),
    
        # chart base
        'base_names': base_names,
        'base_quantity': base_quantities,
        'base_colors': create_rgb_colors(len(base_names)),
    
        # personal table
        'records_personal': records_personal,
    }

    return context

@shared_task
def get_dimension_hole_task(request_get):
    is_filter = False
    filters = list()

    dungeon_runs = DimensionHoleRun.objects.all().order_by('clear_time')

    if request_get:
        is_filter = True

    if 'base' in request_get.keys() and request_get['base'][0] and request_get['base'][0] != '0':
        base = request_get['base'][0].replace('_', ' ')
        filters.append('Base Monster: ' + base)
        dungeon_runs_ids = dungeon_runs.filter(monsters__base_monster__name=base).values_list('id', flat=True)
        dungeon_runs = dungeon_runs.filter(id__in=dungeon_runs_ids)

    if 'dungeon' in request_get.keys() and request_get['dungeon'][0] and request_get['dungeon'][0] != '0':
        dungeon = request_get['dungeon'][0].replace('_', ' ')
        filters.append('Dungeon: ' + dungeon)
        dungeon_runs = dungeon_runs.filter(dungeon=DimensionHoleRun().get_dungeon_id_by_name(dungeon))

    if 'practice' in request_get.keys() and request_get['practice'][0] and request_get['practice'][0] != '0':
        filters.append('Practice Mode: ' + request_get['practice'][0])
        dungeon_runs = dungeon_runs.filter(practice=request_get['practice'][0])

    if 'stage' in request_get.keys() and request_get['stage'][0] and request_get['stage'][0] != '0':
        filters.append('Stage: ' + request_get['stage'][0])
        dungeon_runs = dungeon_runs.filter(stage=int(request_get['stage'][0]))

    if 'secs_min' in request_get.keys() and request_get['secs_min'][0] and request_get['secs_min'][0] != '0':
        filters.append('Faster than: ' + request_get['secs_min'][0] + ' seconds')
        dungeon_runs = dungeon_runs.filter(clear_time__lte=datetime.timedelta(seconds=int(request_get['secs_min'][0])))

    success_rate_min = 0
    if 'success_rate_min' in request_get.keys() and request_get['success_rate_min'][0] and request_get['success_rate_min'][0] != '0':
        filters.append('Success Rate Minimum: ' + request_get['success_rate_min'][0])
        success_rate_min = float(request_get['success_rate_min'][0])

    success_rate_max = 0
    if 'success_rate_max' in request_get.keys() and request_get['success_rate_max'][0] and request_get['success_rate_max'][0] != '0':
        filters.append('Success Rate Maximum: ' + request_get['success_rate_max'][0])
        success_rate_max = float(request_get['success_rate_max'][0])
        

    dungeon_runs = dungeon_runs.prefetch_related('monsters', 'monsters__base_monster')
    dungeon_runs_clear = dungeon_runs.exclude(clear_time__isnull=True).prefetch_related('monsters', 'monsters__base_monster')

    runs_distribution = get_dungeon_runs_distribution(dungeon_runs_clear, 20)
    avg_time = dungeon_runs_clear.aggregate(avg_time=Avg('clear_time'))['avg_time']

    comps = list()
    for _, group in itertools.groupby(list(dungeon_runs.values('id', 'monsters__id')), lambda item: item["id"]):
        mons = [mon['monsters__id'] for mon in group if mon['monsters__id']]
        mons.sort()
        if mons and mons not in comps and len(mons) == 4:
            comps.append(mons)   

    try:
        fastest_run = dungeon_runs_clear.first().clear_time.total_seconds()
    except AttributeError:
        fastest_run = None
    
    records_personal = sorted(get_dimhole_runs_by_comp(comps, dungeon_runs, fastest_run, success_rate_min, success_rate_max), key=itemgetter('sorting_val'), reverse = True)

    dungeon_runs = dungeon_runs_clear # exclude failed runs

    base_names, base_quantities = get_dungeon_runs_by_base_class(dungeon_runs)
    runs_per_dungeon = get_dimhole_runs_per_dungeon(dungeon_runs)
    runs_per_practice = get_dimhole_runs_per_practice(dungeon_runs)
    runs_per_stage = get_dimhole_runs_per_stage(dungeon_runs)

    context = {
        # filters
        'is_filter': is_filter,
        'filters': '[' + ', '.join(filters) + ']',
        'request': request_get,

        # all
        'avg_time': str(avg_time),
        
        # chart distribution
        'runs_distribution': runs_distribution['distribution'],
        'runs_means': runs_distribution['scope'],
        'runs_colors': create_rgb_colors(runs_distribution['interval']),

        # chart base
        'base_names': base_names,
        'base_quantity': base_quantities,
        'base_colors': create_rgb_colors(len(base_names)),

        # chart dungeon
        'dungeon_names': runs_per_dungeon['name'],
        'dungeon_quantity': runs_per_dungeon['quantity'],
        'dungeon_colors': create_rgb_colors(runs_per_dungeon['length']),

        # chart practice mode
        'practice_names': runs_per_practice['name'],
        'practice_quantity': runs_per_practice['quantity'],
        'practice_colors': create_rgb_colors(runs_per_practice['length']),

        # chart stage
        'stage_names': runs_per_stage['name'],
        'stage_quantity': runs_per_stage['quantity'],
        'stage_colors': create_rgb_colors(runs_per_stage['length']),

        # personal table
        'records_personal': records_personal,
    }

    return context
# endregion

# region OTHER
@shared_task
def get_homepage_task():
    """Return the homepage with carousel messages & introduction."""
    runes = Rune.objects.all()
    rune_best = runes.order_by('-efficiency').first()

    monsters = Monster.objects.all()
    monster_best = monsters.order_by('-avg_eff').first()
    monster_cdmg = monsters.order_by('-crit_dmg').first()
    monster_speed = monsters.order_by('-speed').first()
    
    artifacts = Artifact.objects.all()
    
    giants_fastest = DungeonRun.objects.filter(dungeon=8001, stage=10).order_by('clear_time').first()
    dragons_fastest = DungeonRun.objects.filter(dungeon=9001, stage=10).order_by('clear_time').first()
    necropolis_fastest = DungeonRun.objects.filter(dungeon=6001, stage=10).order_by('clear_time').first()
    steel_fastest = DungeonRun.objects.filter(dungeon=9501, stage=10).order_by('clear_time').first()
    punisher_fastest = DungeonRun.objects.filter(dungeon=9502, stage=10).order_by('clear_time').first()

    giants_fastest_b12 = DungeonRun.objects.filter(dungeon=8001, stage=12).order_by('clear_time').first()
    dragons_fastest_b12 = DungeonRun.objects.filter(dungeon=9001, stage=12).order_by('clear_time').first()
    necropolis_fastest_b12 = DungeonRun.objects.filter(dungeon=6001, stage=12).order_by('clear_time').first()

    MESSAGES = [
        {
            'id': 1,
            'title': 'Highest rune efficiency',
            'text': f'The most efficient rune has {rune_best.efficiency if rune_best else 0}% efficiency.',
            'type': 'rune',
            'arg': rune_best.id if rune_best else 0,
        },
        {
            'id': 2,
            'title': 'Runes',
            'text': f'Our database contains {runes.count()} runes',
        },
        {
            'id': 3,
            'title': 'Monsters',
            'text': f'Our database contains {monsters.count()} monsters',
        },
        {
            'id': 4,
            'title': 'Artifacts',
            'text': f'Our database contains {artifacts.count()} artifacts',
        },
        {
            'id': 5,
            'title': 'Highest average efficiency',
            'text': f'{str(monster_best)} has the highest average efficiency -> {monster_best.avg_eff if monster_best else 0}%',
            'type': 'monster',
            'arg': monster_best.id if monster_best else 0,
        },
        {
            'id': 6,
            'title': 'Highest critical damage value',
            'text': f'Highest Critical Damage value ({monster_cdmg.crit_dmg if monster_cdmg else 0}%) has {str(monster_cdmg)}',
            'type': 'monster',
            'arg': monster_cdmg.id if monster_best else 0,
        },
        {
            'id': 7,
            'title': 'Fastest monster',
            'text': f'{str(monster_speed)} has an amazing {monster_speed.speed if monster_speed else 0} SPD',
            'type': 'monster',
            'arg': monster_speed.id if monster_speed else 0,
        },
        {
            'id': 8,
            'title': 'Fastest GB10 Run',
            'text': f'Someone beat Giant\'s Keep B10 in {int(giants_fastest.clear_time.total_seconds())} seconds!',
            'type': 'dungeon',
            'arg': {'dungeon': DungeonRun.get_dungeon_name(giants_fastest.dungeon), 'stage': 10},
        },
        {
            'id': 9,
            'title': 'Fastest DB10 Run',
            'text': f'Someone beat Dragon\'s Lair B10 in {int(dragons_fastest.clear_time.total_seconds())} seconds!',
            'type': 'dungeon',
            'arg': {'dungeon': DungeonRun.get_dungeon_name(dragons_fastest.dungeon), 'stage': 10},
        },
        {
            'id': 10,
            'title': 'Fastest NB10 Run',
            'text': f'Someone beat Necropolis B10 in {int(necropolis_fastest.clear_time.total_seconds())} seconds!',
            'type': 'dungeon',
            'arg': {'dungeon': DungeonRun.get_dungeon_name(necropolis_fastest.dungeon), 'stage': 10},
        },
        
        {
            'id': 11,
            'title': 'Fastest SB10 Run',
            'text': f'Someone beat Steel Fortress B10 in {int(steel_fastest.clear_time.total_seconds())} seconds!',
            'type': 'dungeon',
            'arg': {'dungeon': DungeonRun.get_dungeon_name(steel_fastest.dungeon), 'stage': 10},
        },
        {
            'id': 12,
            'title': 'Fastest PB10 Run',
            'text': f'Someone beat Punisher\'s Crypt B10 in {int(punisher_fastest.clear_time.total_seconds())} seconds!',
            'type': 'dungeon',
            'arg': {'dungeon': DungeonRun.get_dungeon_name(punisher_fastest.dungeon), 'stage': 10},
        },
        {
            'id': 13,
            'title': 'Fastest GB12 Run',
            'text': f'Someone beat Giant\'s Keep B12 in {int(giants_fastest_b12.clear_time.total_seconds())} seconds!',
            'type': 'dungeon',
            'arg': {'dungeon': DungeonRun.get_dungeon_name(giants_fastest_b12.dungeon), 'stage': 12},
        },
        {
            'id': 14,
            'title': 'Fastest DB12 Run',
            'text': f'Someone beat Dragon B12 in {int(dragons_fastest_b12.clear_time.total_seconds())} seconds!',
            'type': 'dungeon',
            'arg': {'dungeon': DungeonRun.get_dungeon_name(dragons_fastest_b12.dungeon), 'stage': 12},
        },
        {
            'id': 15,
            'title': 'Fastest NB12 Run',
            'text': f'Someone beat Necropolis B12 in {int(necropolis_fastest_b12.clear_time.total_seconds())} seconds!',
            'type': 'dungeon',
            'arg': {'dungeon': DungeonRun.get_dungeon_name(necropolis_fastest_b12.dungeon), 'stage': 12},
        },
    ]

    ids = [el['id'] for el in MESSAGES]

    context = {
        'messages': MESSAGES,
        'ids': ids,
    }

    return context

@shared_task
def get_siege_records_task(request_get):
    is_filter = False
    filters = list()
    records = SiegeRecord.objects.filter(full=True)

    if request_get:
        is_filter = True
    
    if 'family' in request_get.keys() and request_get['family'][0] and request_get['family'][0] != '0':
        family = [family_member.replace('_', ' ') for family_member in request_get['family']]
        filters.append('Family: ' + ', '.join(family))
        for member in family:
            records = records.filter(monsters__base_monster__family__name=member)

    if 'attribute' in request_get.keys() and request_get['attribute'] and request_get['attribute'][0] != '0':
        filters.append('Element: ' + request_get['attribute'][0])
        records = records.filter(monsters__base_monster__attribute=MonsterBase().get_attribute_id(request_get['attribute'][0]))
    
    if 'ranking' in request_get.keys() and request_get['ranking'][0] and request_get['ranking'][0] != '0':
        rankings = [ranking for ranking in request_get['ranking']]
        ranking_names = [Guild().get_siege_ranking_name(int(ranking)) for ranking in rankings]
        filters.append('Ranking: ' + ', '.join(ranking_names))
        for ranking in rankings:
            records = records.filter(wizard__guild__siege_ranking=ranking)

    if 'success_rate_min' in request_get.keys() and request_get['success_rate_min'][0] and request_get['success_rate_min'][0] != '0':
        filters.append('Success Rate Minimum: ' + request_get['success_rate_min'][0])
        records = records.filter(ratio__gte=float(request_get['success_rate_min'][0]))

    if 'success_rate_max' in request_get.keys() and request_get['success_rate_max'][0] and request_get['success_rate_max'][0] != '0':
        filters.append('Success Rate Maximum: ' + request_get['success_rate_max'][0])
        records = records.filter(ratio__lte=float(request_get['success_rate_max'][0]))
        

    records = records.prefetch_related('monsters', 'monsters__base_monster', 'wizard', 'wizard__guild', 'monsters__base_monster__family')

    records_by_family = get_siege_records_group_by_family(records)
    records_by_ranking = get_siege_records_group_by_ranking(records)

    records_count = records.count()
    min_records_count = min(100, records_count)

    records_ids = [ record.id for record in records ]
    
    context = {
        # filters
        'is_filter': is_filter,
        'filters': '[' + ', '.join(filters) + ']',
        'request': request_get,

        # table top
        'records_ids': records_ids,
        'best_amount' : min_records_count,

        # chart by monsters family
        'family_name': records_by_family['name'],
        'family_count': records_by_family['quantity'],
        'family_color': create_rgb_colors(records_by_family['length']),

        # chart by ranking
        'ranking_id': records_by_ranking['ids'],
        'ranking_name': records_by_ranking['name'],
        'ranking_count': records_by_ranking['quantity'],
        'ranking_color': create_rgb_colors(records_by_ranking['length']),
    }

    return context

@shared_task
def get_homunculus_base_task(request_get, base):
    is_filter = False
    filters = list()
    homunculuses = WizardHomunculus.objects.filter(homunculus__base_monster__id=base).order_by('-homunculus__avg_eff').prefetch_related('build', 'build__depth_1', 'build__depth_2', 'build__depth_3', 'build__depth_4', 'build__depth_5')
    
    if request_get:
        is_filter = True

    if 'build' in request_get.keys() and request_get['build']:
        homunculuses = homunculuses.filter(build=request_get['build'][0])

    homies_ids = [homie.id for homie in homunculuses]
    homunculus_skills_ids = get_homunculus_skill_description(homunculuses)
    homunculus_chart_builds = get_homunculus_builds(homunculuses)

    context = {
        'records_ids': homies_ids,

        # chart builds
        'builds_name': homunculus_chart_builds['name'],
        'builds_quantity': homunculus_chart_builds['quantity'],
        'builds_color': create_rgb_colors(homunculus_chart_builds['length']),
        'builds_identifier': homunculus_chart_builds['identifier'],

        # table skills
        'skills_ids': homunculus_skills_ids,
    }

    return context

@shared_task
def handle_profile_upload_and_rank_task(data):
    handle_profile_upload_task.s(data).apply()
    
    content = {
        'points': get_scoring_for_profile(data['wizard_info']['wizard_id']),
        'comparison': get_profile_comparison_with_database(data['wizard_info']['wizard_id'])
    }
    
    return content
# endregion

########################### BOT ###########################
@shared_task
def generate_bot_reports(monster_id=None):
    from .views import create_monster_report_by_bot # import locally because of circular import

    if monster_id:
        monsters_base = [monster_id]
    else:
        monsters_base = list(MonsterBase.objects.filter(~Q(archetype=5)).values_list('id', flat=True)) # archetype=5 -> Material Monsters
        monsters_base.sort()
        
    for monster_id in monsters_base:
        if(create_monster_report_by_bot(monster_id)):
            text = "[Bot][Periodic Task] Created report about " + str(monster_id)
            print(text)
        else:
            text = "[Bot][Periodic Task] Error has been raised while creating report about " + str(monster_id)
            print(text)