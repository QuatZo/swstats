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
        for monster in data['unit_list']:
            for rune in monster['runes']:
                temp_runes.append(rune)

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
        parse_wizard_inventory(data['inventory_info'])

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
def handle_raid_start_upload_task(data):
    try:
        logger.debug(f"New Raid has been started")
        obj, created = RaidBattleKey.objects.get_or_create(battle_key=data['battle_info']['battle_key'], defaults={
            'battle_key': data['battle_info']['battle_key'],
            'stage': data['battle_info']['room_info']['stage_id'],
        })
        logger.debug(f"Created new Raid key")
    except Exception as e: # to find all exceptions and fix them without breaking the whole app, it is a temporary solution
        log_exception(e, data=data)

@shared_task
def handle_dungeon_run_upload_task(data_resp, data_req):
    try:
        command = data_resp['command']
        logger.debug(f"Starting Battle Dungeon Result upload for {data_resp['wizard_info']['wizard_id']}")
        dungeon = dict()
        wizard, created = Wizard.objects.update_or_create(id=data_resp['wizard_info']['wizard_id'], defaults=parse_wizard(data_resp['wizard_info'], data_resp['tvalue']))
        dungeon['wizard'] = Wizard.objects.get(id=data_resp['wizard_info']['wizard_id'])
        if command == 'BattleRiftOfWorldsRaidResult':
            dungeon['dungeon'] = 999999999
            rift_battles = RaidBattleKey.objects.filter(battle_key=data_req['battle_key'])
            if not rift_battles.count():
                logging.error(f"Unknown stage for Rift Raid Battle (ID: {data_req['battle_key']})")
                return
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

        monsters = list()
        for temp_monster in data_req['unit_id_list']:
            mon = Monster.objects.filter(id=temp_monster['unit_id'])
            if mon.count() > 0:
                monsters.append(mon.first())

        obj, created = RiftDungeonRun.objects.update_or_create(battle_key=dungeon['battle_key'], defaults=dungeon)
        obj.monsters.set(monsters)
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
                'hour': 0 if int(time_str[:-3]) < 3600 else round(int(time_str[:-3]) / 3600),
                'minute': 0 if int(time_str[:-3]) < 60 else round(int(time_str[:-3]) / 60),
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

########################### WEB ###########################
@shared_task
def get_homepage_task():
    """Return the homepage with carousel messages & introduction."""
    runes = Rune.objects.all()
    rune_best = runes.order_by('-efficiency').first()

    monsters = Monster.objects.all()
    monster_best = monsters.order_by('-avg_eff').first()
    monster_cdmg = monsters.order_by('-crit_dmg').first()
    monster_speed = monsters.order_by('-speed').first()
    
    giants_fastest = DungeonRun.objects.filter(dungeon=8001, stage=10).order_by('clear_time').first()
    dragons_fastest = DungeonRun.objects.filter(dungeon=9001, stage=10).order_by('clear_time').first()
    necropolis_fastest = DungeonRun.objects.filter(dungeon=6001, stage=10).order_by('clear_time').first()

    MESSAGES = [
        {
            'id': 1,
            'title': 'Highest rune efficiency',
            'text': f'The most efficient rune stored in database has {rune_best.efficiency if rune_best else 0}% efficiency.',
            'type': 'rune',
            'arg': rune_best.id if rune_best else 0,
        },
        {
            'id': 2,
            'title': 'Database',
            'text': f'Our datbase contains {runes.count()} runes and {monsters.count()} monsters.',
        },
        {
            'id': 3,
            'title': 'Highest average efficiency',
            'text': f'{str(monster_best)} has the highest average efficiency, amounting to {monster_best.avg_eff if monster_best else 0}%',
            'type': 'monster',
            'arg': monster_best.id if monster_best else 0,
        },
        {
            'id': 4,
            'title': 'Highest critical damage value',
            'text': f'Highest Critical Damage value has {str(monster_cdmg)} with an amazing {monster_cdmg.crit_dmg if monster_cdmg else 0}%',
            'type': 'monster',
            'arg': monster_cdmg.id if monster_best else 0,
        },
        {
            'id': 5,
            'title': 'Fastest monster',
            'text': f'Can something be faster than Flash? Yes! Such a monster is {str(monster_speed)} with an amazing {monster_speed.speed if monster_speed else 0} SPD',
            'type': 'monster',
            'arg': monster_speed.id if monster_speed else 0,
        },
        {
            'id': 6,
            'title': 'Fastest Giant\'s Keep B10 Run',
            'text': f'You don\'t believe it! Someone beat Giant\'s Keep B10 in {int(giants_fastest.clear_time.total_seconds())} seconds!',
            'type': 'dungeon',
            'arg': {'dungeon': DungeonRun.get_dungeon_name(giants_fastest.dungeon), 'stage': 10},
        },
        {
            'id': 7,
            'title': 'Fastest Dragon\'s Lair B10 Run',
            'text': f'Wait, what!? Someone set up Dragon B10 on fire in just {int(dragons_fastest.clear_time.total_seconds())} seconds. Incredible!',
            'type': 'dungeon',
            'arg': {'dungeon': DungeonRun.get_dungeon_name(dragons_fastest.dungeon), 'stage': 10},
        },
        {
            'id': 8,
            'title': 'Fastest Necropolis B10 Run',
            'text': f'The Ancient Lich King was alive only for {int(necropolis_fastest.clear_time.total_seconds())} seconds after resurrection!',
            'type': 'dungeon',
            'arg': {'dungeon': DungeonRun.get_dungeon_name(necropolis_fastest.dungeon), 'stage': 10},
        },
    ]

    ids = [el['id'] for el in MESSAGES]

    context = {
        'messages': MESSAGES,
        'ids': ids,
    }

    return context

@shared_task
def get_runes_task(request_get):
    runes = Rune.objects.order_by('-efficiency')

    is_filter = False 
    filters = list()

    if request_get:
        is_filter = True

    if 'set' in request_get.keys() and request_get['set']:
        filters.append('Set: ' + request_get['set'][0])
        runes = runes.filter(rune_set__name=request_get['set'][0])

    if 'slot' in request_get.keys() and request_get['slot']:
        try:
            slot = int(request_get['slot'][0])
        except ValueError:
            slot = 0
        filters.append('Slot: ' + str(slot))
        runes = runes.filter(slot=slot)
    
    if 'quality' in request_get.keys() and request_get['quality']:
        filters.append('Quality: ' + request_get['quality'][0])
        quality_id = Rune().get_rune_quality_id(request_get['quality'][0])
        runes = runes.filter(quality=quality_id)
    
    if 'quality-original' in request_get.keys() and request_get['quality-original']:
        filters.append('Original Quality: ' + request_get['quality-original'][0])
        quality_original_id = Rune().get_rune_quality_id(request_get['quality-original'][0])
        runes = runes.filter(quality_original=quality_original_id)

    if 'main-stat' in request_get.keys() and request_get['main-stat']:
        main_stat = request_get['main-stat'][0].replace('plus', '+').replace('percent', '%')
        filters.append('Main Stat: ' + main_stat)
        main_stat_id = Rune().get_rune_primary_id(main_stat)
        runes = runes.filter(primary=main_stat_id)
    
    if 'stars' in request_get.keys() and request_get['stars']:
        try:
            stars = int(request_get['stars'][0]) % 10
        except ValueError:
            stars = 0
        filters.append('Stars: ' + str(stars))
        runes = runes.filter(Q(stars=stars) | Q(stars=stars + 10)) # since ancient runes have 11-16

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
    
    context = {
        # filters
        'is_filter': is_filter,
        'filters': '[' + ', '.join(filters) + ']',

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
    runes = Rune.objects.all()

    try:
        rta_monster_id = RuneRTA.objects.filter(rune=rune.id).prefetch_related('monster', 'monster__base_monster', 'rune', 'rune__rune_set').first().monster.id
    except AttributeError:
        rta_monster_id = None

    runes_category_slot = runes.filter(slot=rune.slot)
    runes_category_set = runes.filter(rune_set=rune.rune_set)
    runes_category_both = runes.filter(slot=rune.slot, rune_set=rune.rune_set)

    similar_ids = get_rune_similar(runes, rune)

    ranks = {
        'normal': {
            'efficiency': get_rune_rank_eff(runes, rune),
            'hp_flat': get_rune_rank_substat(runes, rune, 'sub_hp_flat'),
            'hp': get_rune_rank_substat(runes, rune, 'sub_hp'),
            'atk_flat': get_rune_rank_substat(runes, rune, 'sub_atk_flat'),
            'atk': get_rune_rank_substat(runes, rune, 'sub_atk'),
            'def_flat': get_rune_rank_substat(runes, rune, 'sub_def_flat'),
            'def': get_rune_rank_substat(runes, rune, 'sub_def'),
            'speed': get_rune_rank_substat(runes, rune, 'sub_speed'),
            'crit_rate': get_rune_rank_substat(runes, rune, 'sub_crit_rate'),
            'crit_dmg': get_rune_rank_substat(runes, rune, 'sub_crit_dmg'),
            'res': get_rune_rank_substat(runes, rune, 'sub_res'),
            'acc': get_rune_rank_substat(runes, rune, 'sub_acc'),
        },
        'categorized': {
            'efficiency_slot': get_rune_rank_eff(runes_category_slot, rune),
            'efficiency_set': get_rune_rank_eff(runes_category_set, rune),
            'efficiency_both': get_rune_rank_eff(runes_category_both, rune),
            'speed_slot': get_rune_rank_substat(runes_category_slot, rune, 'sub_speed', ['slot']),
            'speed_set': get_rune_rank_substat(runes_category_set, rune, 'sub_speed', ['set']),
            'speed_both': get_rune_rank_substat(runes_category_both, rune, 'sub_speed', ['slot', 'set']),
        }
    }

    context = {
        'rta_monster_id': rta_monster_id,
        'ranks': ranks,
        'similar_ids': similar_ids,
        'arg_id': arg_id,
    }

    return context

@shared_task
def get_monsters_task(request_get):
    monsters = Monster.objects.order_by('-avg_eff')   
    is_filter = False 
    filters = list()

    if request_get:
        is_filter = True

    if 'family' in request_get.keys() and request_get['family']:
        family = request_get['family'][0].replace('_', ' ')
        filters.append('Family: ' + family)
        monsters = monsters.filter(base_monster__family__name=family)

    if 'attribute' in request_get.keys() and request_get['attribute']:
        filters.append('Attribute: ' + request_get['attribute'][0])
        monsters = monsters.filter(base_monster__attribute=MonsterBase().get_attribute_id(request_get['attribute'][0]))

    if 'type' in request_get.keys() and request_get['type']:
        filters.append('Type: ' + request_get['type'][0])
        monsters = monsters.filter(base_monster__archetype=MonsterBase().get_archetype_id(request_get['type'][0]))
    
    if 'base-class' in request_get.keys() and request_get['base-class']:
        filters.append('Base Class: ' + request_get['base-class'][0])
        monsters = monsters.filter(base_monster__base_class=request_get['base-class'][0])
    
    if 'storage' in request_get.keys() and request_get['storage']:
        filters.append('Storage: ' + request_get['storage'][0])
        monsters = monsters.filter(storage=request_get['storage'][0])

    if 'hoh' in request_get.keys() and request_get['hoh']:
        filters.append('HoH: ' + request_get['hoh'][0])
        if request_get['hoh'][0] == "True":
            monsters = monsters.filter(base_monster__in=get_monsters_hoh())
        else:
            monsters = monsters.exclude(base_monster__in=get_monsters_hoh())
    
    if 'fusion' in request_get.keys() and request_get['fusion']:
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
    
    best_monsters_ids = [monster.id for monster in get_monster_list_best(monsters, 100, monsters_count)]
    fastest_monsters_ids = [monster.id for monster in get_monster_list_fastest(monsters, 100, monsters_count)]
    toughest_monsters_ids = [monster.id for monster in get_monster_list_toughest(monsters, 100, monsters_count)]
    toughest_def_break_monsters_ids = [monster.id for monster in get_monster_list_toughest_def_break(monsters, 100, monsters_count)]

    context = {
        # filters
        'is_filter': is_filter,
        'filters': '[' + ', '.join(filters) + ']',

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

        # table best by Effective HP
        'toughest_monsters_ids': toughest_monsters_ids,
        'toughest_amount': len(toughest_monsters_ids),

        # table best by Effective HP while Defense Broken
        'toughest_def_break_monsters_ids': toughest_def_break_monsters_ids,
        'toughest_def_break_amount': len(toughest_def_break_monsters_ids),
    }

    return context

@shared_task
def get_monster_by_id_task(request_get, arg_id):
    monsters = Monster.objects.all().order_by('-avg_eff')
    monster = get_object_or_404(Monster.objects.prefetch_related('runes', 'runes__rune_set', 'base_monster', 'runes__equipped_runes', 'runes__equipped_runes__base_monster', 'siege_defense_monsters'), id=arg_id)
    
    rta_monsters = RuneRTA.objects.filter(monster=arg_id).prefetch_related('rune', 'rune__rune_set', 'monster', 'monster__base_monster')

    rta_build = list()
    for rta_monster in rta_monsters:
        rta_build.append(rta_monster.rune)

    try:
        rta_eff = round(sum([ rune.efficiency for rune in rta_build ]) / len(rta_build), 2)
    except ZeroDivisionError:
        rta_eff = None

    monsters_category_base = monsters.filter(base_monster=monster.base_monster)
    monsters_category_family = monsters.filter(base_monster__family=monster.base_monster.family)
    monsters_category_attribute = monsters.filter(base_monster__attribute=monster.base_monster.attribute)
    monsters_category_type = monsters.filter(base_monster__archetype=monster.base_monster.archetype)
    monsters_category_attr_type = monsters.filter(base_monster__attribute=monster.base_monster.attribute, base_monster__archetype=monster.base_monster.archetype)
    monsters_category_base_class = monsters.filter(base_monster__base_class=monster.base_monster.base_class)
    monsters_category_all = monsters_category_attr_type.filter(base_monster__base_class=monster.base_monster.base_class)

    rta_similar_builds = dict()
    for rta_similar in RuneRTA.objects.filter(monster__base_monster__family=monster.base_monster.family, monster__base_monster__attribute=monster.base_monster.attribute).exclude(monster=monster.id):
        if rta_similar.monster.id not in rta_similar_builds.keys():
            rta_similar_builds[rta_similar.monster.id] = list()
        rta_similar_builds[rta_similar.monster.id].append(rta_similar.rune.id)

    
    MAX_COUNT = 20
    mon_similar_builds = list(monsters.filter(base_monster__attribute=monster.base_monster.attribute, base_monster__family=monster.base_monster.family).exclude(id=monster.id).values_list('id', flat=True))
    mon_similar_builds = random.sample(mon_similar_builds, min(MAX_COUNT, len(mon_similar_builds)))

    rta_final_similar_builds = dict()
    for key in random.sample(rta_similar_builds.keys(), min(MAX_COUNT, len(rta_similar_builds))):
        rta_final_similar_builds[key] = rta_similar_builds[key]
    rta_similar_builds = rta_final_similar_builds

    monsters_count = monsters.count()

    ranks = {
        'normal': {
            'avg_eff': get_monster_rank_avg_eff(monsters, monster),
            'hp': get_monster_rank_stats(monsters, monster, 'hp', monsters_count),
            'attack': get_monster_rank_stats(monsters, monster, 'attack', monsters_count),
            'defense': get_monster_rank_stats(monsters, monster, 'defense', monsters_count),
            'speed': get_monster_rank_stats(monsters, monster, 'speed', monsters_count),
            'res': get_monster_rank_stats(monsters, monster, 'res', monsters_count),
            'acc': get_monster_rank_stats(monsters, monster, 'acc', monsters_count),
            'crit_rate': get_monster_rank_stats(monsters, monster, 'crit_rate', monsters_count),
            'crit_dmg': get_monster_rank_stats(monsters, monster, 'crit_dmg', monsters_count),
            'eff_hp': get_monster_rank_stats(monsters, monster, 'eff_hp', monsters_count),
            'eff_hp_def_break': get_monster_rank_stats(monsters, monster, 'eff_hp_def_break', monsters_count),
        },
        'categorized': {
            'avg_eff_base': get_monster_rank_avg_eff(monsters_category_base, monster),
            'avg_eff_family': get_monster_rank_avg_eff(monsters_category_family, monster),
            'avg_eff_attribute': get_monster_rank_avg_eff(monsters_category_attribute, monster),
            'avg_eff_type': get_monster_rank_avg_eff(monsters_category_type, monster),
            'avg_eff_attr_type': get_monster_rank_avg_eff(monsters_category_attr_type, monster),
            'avg_eff_base_class': get_monster_rank_avg_eff(monsters_category_base_class, monster),
            'avg_eff_all': get_monster_rank_avg_eff(monsters_category_all, monster),
        }
    }

    rta = {
        'build_ids': [rune.id for rune in rta_build],
        'eff': rta_eff,
    }

    context = {
        'ranks': ranks,
        'rta': rta,
        'similar_ids': mon_similar_builds,
        'rta_similar_ids': rta_similar_builds,
        'decks_ids': [deck.id for deck in Deck.objects.filter(monsters__id=monster.id)],
    }

    return context

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

    if 'base' in request_get.keys() and request_get['base']:
        base = request_get['base'][0].replace('_', ' ')
        filters.append('Base Monster: ' + base)
        dungeon_runs_ids = dungeon_runs.filter(monsters__base_monster__name=base).values_list('id', flat=True)
        dungeon_runs = dungeon_runs.filter(id__in=dungeon_runs_ids)
        
    dungeon_runs_clear = dungeon_runs.exclude(clear_time__isnull=True).prefetch_related('monsters', 'monsters__base_monster')
    runs_distribution = get_dungeon_runs_distribution(dungeon_runs_clear, 20)
    avg_time = dungeon_runs_clear.aggregate(avg_time=Avg('clear_time'))['avg_time']

    dungeon_runs = dungeon_runs.prefetch_related('monsters')
    
    comps = list()
    nulls = 0
    for _, group in itertools.groupby(list(dungeon_runs.values('id', 'dungeon', 'monsters__id')), lambda item: item["id"]):
        results = np.array([[mon['monsters__id'], mon['dungeon']] for mon in group if mon['monsters__id']])
        if not results.shape[0]:
            continue
        mons = results[:, 0].tolist()
        dungeon_id = results[0, 1]
        mons.sort()
        if mons and mons not in comps and len(mons) == get_comp_count(dungeon_id):
            comps.append(mons)    

    try:
        fastest_run = dungeon_runs_clear.order_by('clear_time').first().clear_time.total_seconds()
    except AttributeError:
        fastest_run = None

    records_personal = sorted(get_dungeon_runs_by_comp(comps, dungeon_runs, fastest_run), key=itemgetter('sorting_val'), reverse = True)
    base_names, base_quantities = get_dungeon_runs_by_base_class(dungeon_runs_clear)

    context = {
        # filters
        'is_filter': is_filter,
        'filters': '[' + ', '.join(filters) + ']',

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
def get_rift_dungeon_by_stage_task(request_get, name):
    is_filter = False
    filters = list()
    names = name.split('-')

    for i in range(len(names)):
        if names[i] != "of":
            names[i] = names[i].capitalize()
    name = ' '.join(names)

    dungeon_runs = RiftDungeonRun.objects.filter(dungeon=RiftDungeonRun().get_dungeon_id(name)).exclude(clear_rating=None)
    if request_get:
        is_filter = True

    if 'base' in request_get.keys() and request_get['base']:
        base = request_get['base'][0].replace('_', ' ')
        filters.append('Base Monster: ' + base)
        dungeon_runs_ids = dungeon_runs.filter(monsters__base_monster__name=base).values_list('battle_key', flat=True)
        dungeon_runs = dungeon_runs.filter(battle_key__in=dungeon_runs_ids)
    
    dungeon_runs = dungeon_runs.prefetch_related('monsters', 'monsters__base_monster')
    dungeon_runs_clear = dungeon_runs.exclude(clear_time__isnull=True)
    
    damage_distribution = get_rift_dungeon_damage_distribution(dungeon_runs, 20)
    avg_time = dungeon_runs_clear.aggregate(avg_time=Avg('clear_time'))['avg_time']


    comps = list()
    for _, group in itertools.groupby(list(dungeon_runs.values('battle_key', 'monsters__id')), lambda item: item["battle_key"]):
        mons = [mon['monsters__id'] for mon in group if mon['monsters__id']]
        mons.sort()
        if mons and mons not in comps and len(mons) == 6:
            comps.append(mons)  

    try:
        highest_damage = dungeon_runs.order_by('-dmg_total').first().dmg_total
    except AttributeError:
        highest_damage = None

    records_personal = sorted(get_rift_dungeon_runs_by_comp(comps, dungeon_runs, highest_damage), key=itemgetter('sorting_val'), reverse = True)
    base_names, base_quantities = get_dungeon_runs_by_base_class(dungeon_runs)

    context = {
        # filters
        'is_filter': is_filter,
        'filters': '[' + ', '.join(filters) + ']',
    
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
    records_ok = False

    dungeon_runs = DimensionHoleRun.objects.all().order_by('clear_time')

    if request_get:
        is_filter = True

    if 'base' in request_get.keys() and request_get['base']:
        base = request_get['base'][0].replace('_', ' ')
        filters.append('Base Monster: ' + base)
        dungeon_runs_ids = dungeon_runs.filter(monsters__base_monster__name=base).values_list('id', flat=True)
        dungeon_runs = dungeon_runs.filter(id__in=dungeon_runs_ids)

    if 'dungeon' in request_get.keys() and request_get['dungeon']:
        dungeon = request_get['dungeon'][0].replace('_', ' ')
        filters.append('Dungeon: ' + dungeon)
        dungeon_runs = dungeon_runs.filter(dungeon=DimensionHoleRun().get_dungeon_id_by_name(dungeon))

    if 'practice' in request_get.keys() and request_get['practice']:
        filters.append('Practice Mode: ' + request_get['practice'][0])
        dungeon_runs = dungeon_runs.filter(practice=request_get['practice'][0])

    if 'stage' in request_get.keys() and request_get['stage']:
        filters.append('Stage: ' + request_get['stage'][0])
        dungeon_runs = dungeon_runs.filter(stage=int(request_get['stage'][0]))

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
    
    if 'stage' in request_get.keys() and request_get['stage'] and 'dungeon' in request_get.keys() and request_get['dungeon']:
        records_ok = True
        records_personal = sorted(get_dimhole_runs_by_comp(comps, dungeon_runs, fastest_run), key=itemgetter('sorting_val'), reverse = True)
    else:
        records_personal = "Pick dungeon & stage to see recorded comps."

    dungeon_runs = dungeon_runs_clear # exclude failed runs

    base_names, base_quantities = get_dungeon_runs_by_base_class(dungeon_runs)
    runs_per_dungeon = get_dimhole_runs_per_dungeon(dungeon_runs)
    runs_per_practice = get_dimhole_runs_per_practice(dungeon_runs)
    runs_per_stage = get_dimhole_runs_per_stage(dungeon_runs)

    context = {
        # filters
        'is_filter': is_filter,
        'filters': '[' + ', '.join(filters) + ']',

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
        'records_ok': records_ok,
        'records_personal': records_personal,
    }

    return context

@shared_task
def get_siege_records_task(request_get):
    is_filter = False
    filters = list()
    records = SiegeRecord.objects.filter(full=True)

    if request_get:
        is_filter = True
    
    if 'family' in request_get.keys() and request_get['family']:
        family = [family_member.replace('_', ' ') for family_member in request_get['family']]
        filters.append('Family: ' + ', '.join(family))
        for member in family:
            records = records.filter(monsters__base_monster__family__name=member)

    if 'ranking' in request_get.keys() and request_get['ranking']:
        rankings = [ranking for ranking in request_get['ranking']]
        ranking_names = [Guild().get_siege_ranking_name(int(ranking)) for ranking in rankings]
        filters.append('Ranking: ' + ', '.join(ranking_names))
        for ranking in rankings:
            records = records.filter(wizard__guild__siege_ranking=ranking)

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

########################### BOT ###########################
@shared_task
def generate_bot_reports(monster_id=None):
    from .views import create_monster_report_by_bot # import locally because of circular import

    if monster_id:
        monsters_base = [monster_id]
    else:
        monsters_base = list(MonsterBase.objects.filter(~Q(archetype=5) & ~Q(awaken=0)).values_list('id', flat=True)) # archetype=5 -> Material Monsters, awaken=0 -> Unawakened
        monsters_base.sort()
        
    for monster_id in monsters_base:
        if(create_monster_report_by_bot(monster_id)):
            text = "[Bot][Periodic Task] Created report about " + str(monster_id)
            print(text)
        else:
            text = "[Bot][Periodic Task] Error has been raised while creating report about " + str(monster_id)
            print(text)