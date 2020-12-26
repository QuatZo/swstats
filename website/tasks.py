from celery import shared_task, group
from django.db import transaction
from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string

from .models import *
from .functions import *
from .views.report import get_monster_info, generate_plots
from .celery import app as celery_app

import requests
import logging
import datetime
import pickle
import time
import itertools
import math
import numpy as np
from operator import itemgetter
import itertools

logger = logging.getLogger(__name__)


########################## UPLOAD #########################
@shared_task
def handle_profile_upload_task(data):
    try:
        with transaction.atomic():
            if 'guild' not in data:
                return
            profile_guild = True
            if data['guild']['guild_info'] is None:
                logger.debug(
                    f"Profile {data['wizard_info']['wizard_id']} has no guild.")
                profile_guild = False
            else:
                logger.debug(
                    f"Checking if guild {data['guild']['guild_info']['guild_id']} exists...")
                guild = Guild.objects.filter(
                    id=data['guild']['guild_info']['guild_id'])
                guild_uptodate = False
                if guild.exists():
                    logger.debug(
                        f"Guild {data['guild']['guild_info']['guild_id']} exists... Checking if it's up-to-date...")
                    guild = guild.filter(
                        last_update__gte=datetime.datetime.utcfromtimestamp(data['tvalue']))
                    if guild.exists():
                        logger.debug(
                            f"Guild {data['guild']['guild_info']['guild_id']} profile is up-to-date.")
                        guild_uptodate = True
                    else:
                        logger.debug(
                            f"Updating guild profile {data['guild']['guild_info']['guild_id']}")
                else:
                    logger.debug(
                        f"Guild profile does NOT exists. Starting first-time guild profile upload for {data['guild']['guild_info']['guild_id']}")

            if (
                profile_guild
                and not guild_uptodate
                and 'guild' in data
                and 'guild_info' in data['guild']
                and 'guildwar_ranking_stat' in data
                and 'best' in data['guildwar_ranking_stat']
                and 'tvalue' in data
            ):
                parse_guild(data['guild']['guild_info'],
                            data['guildwar_ranking_stat']['best'], data['tvalue'])

            logger.debug(
                f"Checking if profile {data['wizard_info']['wizard_id']} exists...")
            wiz = Wizard.objects.filter(id=data['wizard_info']['wizard_id'])
            wizard_uptodate = False
            if wiz.exists():
                logger.debug(
                    f"Profile {data['wizard_info']['wizard_id']} exists... Checking if it's up-to-date...")
                wizard = wiz.filter(
                    last_update__gte=datetime.datetime.utcfromtimestamp(data['tvalue']))
                if wizard.exists():
                    logger.debug(
                        f"Wizard profile {data['wizard_info']['wizard_id']} is up-to-date")
                    wizard_uptodate = True
                else:
                    logger.debug(
                        f"Updating profile {data['wizard_info']['wizard_id']}")
            else:
                logger.debug(
                    f"Profile {data['wizard_info']['wizard_id']} does NOT exists. Starting first-time profile upload")

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
            if 'quiz_reward_info' in data and 'reward_count' in data['quiz_reward_info']:
                wizard['antibot_count'] = data['quiz_reward_info']['reward_count']

            if 'raid_info_list' in data and len(data['raid_info_list']) > 0 and 'available_stage_id' in data['raid_info_list'][0]:
                wizard['raid_level'] = data['raid_info_list'][0]['available_stage_id']

            if 'unit_depository_slots' in data and 'number' in data['unit_depository_slots']:
                wizard['storage_capacity'] = data['unit_depository_slots']['number']

            if profile_guild:
                wizard_guilds = Guild.objects.filter(
                    id=data['guild']['guild_info']['guild_id'])
                if wizard_guilds.count() > 0:
                    wizard['guild'] = wizard_guilds.first()
            else:
                wizard['guild'] = None
            wizard, _ = Wizard.objects.update_or_create(
                id=wizard['id'], defaults=wizard, )
            ########################################

            rune_sets = {rs.id: rs for rs in RuneSet.objects.all()}
            for temp_rune in temp_runes:
                parse_rune(temp_rune, wizard, rune_sets,
                           data['rune_lock_list'])

            for temp_artifact in temp_artifacts:
                parse_artifact(temp_artifact, wizard)

            temp_runes_rta = dict()
            if 'world_arena_rune_equip_list' in data.keys():
                for temp_rune_rta in data['world_arena_rune_equip_list']:
                    if temp_rune_rta['occupied_id'] not in temp_runes_rta.keys():
                        temp_runes_rta[temp_rune_rta['occupied_id']] = list()
                    temp_runes_rta[temp_rune_rta['occupied_id']].append(
                        temp_rune_rta['rune_id'])
                temp_instances = Rune.objects.filter(
                    id__in=[item for record in temp_runes_rta.values() for item in record])
                temp_instances.equipped_rta = True
                Rune.objects.bulk_update(
                    temp_instances, ['equipped_rta'], batch_size=100)

            temp_artifacts_rta = dict()
            if 'world_arena_artifact_equip_list' in data.keys():
                for temp_artifact_rta in data['world_arena_artifact_equip_list']:
                    if temp_artifact_rta['occupied_id'] not in temp_artifacts_rta.keys():
                        temp_artifacts_rta[temp_artifact_rta['occupied_id']] = list(
                        )
                    temp_artifacts_rta[temp_artifact_rta['occupied_id']].append(
                        temp_artifact_rta['artifact_id'])
                temp_instances = Artifact.objects.filter(
                    id__in=[item for record in temp_artifacts_rta.values() for item in record])
                temp_instances.equipped_rta = True
                Artifact.objects.bulk_update(
                    temp_instances, ['equipped_rta'], batch_size=100)

            for temp_monster in data['unit_list']:
                mon_runes_rta = temp_runes_rta[temp_monster['unit_id']
                                               ] if temp_monster['unit_id'] in temp_runes_rta.keys() else list()
                mon_artifacts_rta = temp_artifacts_rta[temp_monster['unit_id']
                                                       ] if temp_monster['unit_id'] in temp_artifacts_rta.keys() else list()
                parse_monster(temp_monster, wizard, data['building_list'],
                              data['unit_lock_list'], mon_runes_rta, mon_artifacts_rta)

            # monster rep
            MonsterRep.objects.update_or_create(wizard=wizard, defaults={
                'wizard': wizard,
                'monster': Monster.objects.get(id=temp_wizard['rep_unit_id'])
            }, )

            parse_decks(data['deck_list'], wizard)
            parse_wizard_buildings(data['deco_list'], wizard)
            if 'pvp_info' in data:
                parse_arena_records(
                    data['pvp_info'], data['defense_unit_list'], wizard)
            parse_wizard_homunculus(data['homunculus_skill_list'], wizard)

            logger.debug(
                f"Fully uploaded profile for {data['wizard_info']['wizard_id']}")
    except Exception as e:  # to find all exceptions and fix them without breaking the whole app, it is a temporary solution
        log_exception(e, data=data)


@shared_task
def handle_friend_upload_task(data):
    try:
        with transaction.atomic():
            temp_wizard = data['friend']
            if 'wizard_id' not in temp_wizard.keys():
                logger.debug(f"[Friend Upload] No Wizard ID. Ending...")
                return

            wizard_id = temp_wizard['wizard_id']
            logger.debug(
                f"[Friend Upload] Checking if profile {wizard_id} exists...")

            # don't overwrite complete data with incomplete
            if Wizard.objects.filter(id=wizard_id).exists():
                logger.debug(
                    f"[Friend Upload] Profile {wizard_id} exists... Ending... ")
                return

            logger.debug(
                f"[Friend Upload] Profile {wizard_id} does NOT exists. Starting first-time profile upload")
            wizard = parse_wizard(temp_wizard, data['tvalue'])
            wizard['id'] = wizard_id
            wizard, _ = Wizard.objects.update_or_create(
                id=wizard['id'], defaults=wizard, )

            rune_sets = {rs.id: rs for rs in RuneSet.objects.all()}
            for temp_monster in temp_wizard['unit_list']:
                good = True
                for rune in temp_monster['runes']:
                    if type(rune) is str:
                        good = False
                        break
                    parse_rune(rune, wizard, rune_sets)
                if good:
                    for artifact in temp_monster['artifacts']:
                        if type(artifact) is str:
                            good = False
                            break
                        parse_artifact(artifact, wizard)
                if good:
                    parse_monster(temp_monster, wizard,
                                  temp_wizard['building_list'], )

            parse_wizard_buildings(temp_wizard['deco_list'], wizard)

            logger.debug(
                f"[Friend Upload] Fully uploaded profile for {wizard_id}")
    except Exception as e:  # to find all exceptions and fix them without breaking the whole app, it is a temporary solution
        log_exception(e, data=data)


@shared_task
def handle_raid_start_upload_task(data_resp, data_req):
    try:
        with transaction.atomic():
            dungeon = dict()

            dungeon['battle_key'] = data_req['battle_key']
            dungeon['stage'] = data_resp['battle_info']['room_info']['stage_id']
            dungeon['date'] = datetime.datetime.utcfromtimestamp(
                data_resp['tvalue'])
            wizard, _ = Wizard.objects.update_or_create(
                id=data_req['wizard_id'], defaults=parse_wizard(data_resp['wizard_info'], data_resp['tvalue']))
            dungeon['wizard'] = wizard

            for user in data_resp['battle_info']['user_list']:
                if user['wizard_id'] == data_req['wizard_id']:
                    monsters = {
                        m['unit_info']['unit_id']: {
                            'leader': m['leader'],
                            'slot': m['index']
                        } for m in user['deck_list']
                    }
                    m_inst = Monster.objects.filter(
                        id__in=[m for m in monsters.keys()])
                    for mon in m_inst:
                        dungeon['monster_' +
                                str(monsters[mon.id]['slot'])] = mon
                        if monsters[mon.id]['leader']:
                            dungeon['leader'] = mon

            _, _ = RaidDungeonRun.objects.update_or_create(
                battle_key=dungeon['battle_key'], defaults=dungeon)
            logger.debug(
                f"Successfully created Rift of Worlds (R{dungeon['stage']}) Start for {data_req['wizard_id']}")
    except Exception as e:  # to find all exceptions and fix them without breaking the whole app, it is a temporary solution
        log_exception(e, data_resp=data_resp, data_req=data_req)


@shared_task
def handle_raid_run_upload_task(data_resp, data_req):
    try:
        with transaction.atomic():
            raid = RaidDungeonRun.objects.get(
                battle_key=data_req['battle_key'])
            if data_req['win_lose'] == 1:
                raid.win = True
                time_str = str(data_req['clear_time'])
                _time = {
                    'hour': 0 if int(time_str[:-3]) < 3600 else math.floor(int(time_str[:-3]) / 3600),
                    'minute': 0 if int(time_str[:-3]) < 60 else math.floor(int(time_str[:-3]) / 60),
                    'second': int(time_str[:-3]) if int(time_str[:-3]) < 60 else int(time_str[:-3]) % 60,
                    'microsecond': int(time_str[-3:]) * 1000,
                }
                raid.clear_time = datetime.time(
                    _time['hour'], _time['minute'], _time['second'], _time['microsecond'])
            else:
                raid.win = False

            raid.save()
            logger.debug(
                f"Successfully created Rift of Worlds Run for {data_req['wizard_id']}")
    except RaidDungeonRun.DoesNotExist:
        return
    except Exception as e:  # to find all exceptions and fix them without breaking the whole app, it is a temporary solution
        log_exception(e, data_resp=data_resp, data_req=data_req)


@shared_task
def handle_dungeon_run_upload_task(data_resp, data_req):
    try:
        with transaction.atomic():
            logger.debug(
                f"Starting Battle Dungeon Result upload for {data_resp['wizard_info']['wizard_id']}")
            dungeon = dict()
            wizard, _ = Wizard.objects.update_or_create(
                id=data_resp['wizard_info']['wizard_id'], defaults=parse_wizard(data_resp['wizard_info'], data_resp['tvalue']))
            dungeon['wizard'] = wizard
            dungeon['dungeon'] = data_req['dungeon_id']
            dungeon['stage'] = data_req['stage_id']
            dungeon['date'] = datetime.datetime.utcfromtimestamp(
                data_resp['tvalue'])

            if data_resp['win_lose'] == 1:
                dungeon['win'] = True
                if 'clear_time' not in data_resp:
                    return  # HOH Dungeon
                time_str = str(data_resp['clear_time']['current_time'])
                _time = {
                    'hour': 0 if int(time_str[:-3]) < 3600 else math.floor(int(time_str[:-3]) / 3600),
                    'minute': 0 if int(time_str[:-3]) < 60 else math.floor(int(time_str[:-3]) / 60),
                    'second': int(time_str[:-3]) if int(time_str[:-3]) < 60 else int(time_str[:-3]) % 60,
                    'microsecond': int(time_str[-3:]) * 1000,
                }
                dungeon['clear_time'] = datetime.time(
                    _time['hour'], _time['minute'], _time['second'], _time['microsecond'])
            else:
                dungeon['win'] = False

            monsters = Monster.objects.filter(id__in=[m['unit_id'] if not isinstance(
                m['unit_id'], dict) else m['unit_id']['unit_id'] for m in data_req['unit_id_list']])

            obj, _ = DungeonRun.objects.update_or_create(
                wizard=dungeon['wizard'], date=dungeon['date'], defaults=dungeon)
            obj.monsters.set(monsters)
            obj.save()
            logger.debug(
                f"Successfuly created Battle Dungeon ({dungeon['dungeon']}) Result for {data_resp['wizard_info']['wizard_id']}")
    except Exception as e:  # to find all exceptions and fix them without breaking the whole app, it is a temporary solution
        log_exception(e, data_resp=data_resp, data_req=data_req)


@shared_task
def handle_rift_dungeon_start_upload_task(data_resp, data_req):
    try:
        with transaction.atomic():
            dungeon = dict()

            dungeon['battle_key'] = data_resp['battle_key']
            dungeon['dungeon'] = data_req['dungeon_id']
            dungeon['date'] = datetime.datetime.utcfromtimestamp(
                data_resp['tvalue'])
            wizard, _ = Wizard.objects.update_or_create(
                id=data_resp['wizard_info']['wizard_id'], defaults=parse_wizard(data_resp['wizard_info'], data_resp['tvalue']))
            dungeon['wizard'] = wizard

            monsters = {
                m['unit_id']: m['slot_index'] for m in data_req['unit_id_list']
            }
            m_inst = Monster.objects.filter(
                id__in=[m for m in monsters.keys()])
            for mon in m_inst:
                dungeon['monster_' +
                        str(monsters[mon.id])] = mon
                if monsters[mon.id] == data_req['leader_index']:
                    dungeon['leader'] = mon

            _, _ = RiftDungeonRun.objects.update_or_create(
                battle_key=dungeon['battle_key'], defaults=dungeon)
            logger.debug(
                f"Successfuly created Rift Dungeon ({dungeon['dungeon']}) Start for {data_resp['wizard_info']['wizard_id']}")
    except Exception as e:  # to find all exceptions and fix them without breaking the whole app, it is a temporary solution
        log_exception(e, data_resp=data_resp, data_req=data_req)


@shared_task
def handle_rift_dungeon_run_upload_task(data_resp, data_req):
    try:
        with transaction.atomic():
            rift = RiftDungeonRun.objects.get(
                battle_key=data_req['battle_key'])
            rift.win = True if data_req['battle_result'] == 1 else False
            rift.clear_rating = data_resp['rift_dungeon_box_id']

            # need to check if always table like this
            dmg_records = data_req['round_list']
            rift.dmg_phase_1 = dmg_records[0][1]
            if len(dmg_records) > 1:
                rift.dmg_phase_glory = dmg_records[1][1]
            if len(dmg_records) > 2:
                rift.dmg_phase_2 = dmg_records[2][1]

            rift.save()
            logger.debug(
                f"Successfuly created Rift Dungeon Result (ID: {data_req['battle_key']})")
    except RiftDungeonRun.DoesNotExist:
        return
    except Exception as e:  # to find all exceptions and fix them without breaking the whole app, it is a temporary solution
        log_exception(e, data_resp=data_resp, data_req=data_req)


@shared_task
def handle_siege_defenses_upload_task(data):
    try:
        with transaction.atomic():
            defenses = list()
            temp_mons = dict()

            wizards = {w.id: w for w in Wizard.objects.all()}

            for deck in data['defense_deck_list']:
                wizard = wizards[deck['wizard_id']]
                if not wizard:
                    continue
                temp_mons[deck['deck_id']] = list()
                defenses.append({
                    'id': deck['deck_id'],
                    'win': deck['win_count'],
                    'lose': deck['lose_count'],
                    'ratio': deck['winning_rate'],
                    'wizard': wizard,
                    'last_update': datetime.datetime.utcfromtimestamp(data['tvalue']),
                })

            for deck_units in data['defense_unit_list']:
                if 'unit_info' in deck_units.keys():
                    for defense in defenses:
                        if defense['id'] == deck_units['deck_id'] and len(temp_mons[deck_units['deck_id']]) < 3:
                            monster = Monster.objects.filter(
                                id=deck_units['unit_info']['unit_id'])
                            monster_first = monster.first()
                            if monster.exists():
                                temp_mons[deck_units['deck_id']].append(
                                    monster_first)
                                if deck_units['pos_id'] == 1:
                                    defense['leader'] = monster_first

            for defense in defenses:
                obj, created = SiegeRecord.objects.update_or_create(
                    id=defense['id'], defaults=defense)
                obj.monsters.set(temp_mons[defense['id']])
                guild = Guild.objects.filter(
                    id=data['wizard_info_list'][0]['guild_id'])
                if guild.exists():
                    defense['wizard'].guild = guild.first()
                    defense['wizard'].save()
                obj.save()
            logger.debug(f"Fully uploaded Siege Defenses")
    except Exception as e:  # to find all exceptions and fix them without breaking the whole app, it is a temporary solution
        log_exception(e, data=data)


@shared_task
def handle_siege_ranking_upload_task(data):
    try:
        Guild.objects.filter(id=data['guildsiege_stat_info']['curr']['guild_id']).update(
            siege_ranking=data['guildsiege_stat_info']['curr']['rating_id'])
    except Exception as e:  # to find all exceptions and fix them without breaking the whole app, it is a temporary solution
        log_exception(e, data=data)


@shared_task
def handle_dimension_hole_run_upload_task(data_resp, data_req):
    try:
        with transaction.atomic():
            logger.debug(
                f"Starting Dimension Hole Run upload for {data_resp['wizard_info']['wizard_id']}")
            dungeon = dict()
            wizard, _ = Wizard.objects.update_or_create(
                id=data_resp['wizard_info']['wizard_id'], defaults=parse_wizard(data_resp['wizard_info'], data_resp['tvalue']))
            dungeon['id'] = data_req['battle_key']
            dungeon['wizard'] = wizard
            dungeon['dungeon'] = data_resp['dungeon_id']
            dungeon['stage'] = data_resp['difficulty']
            dungeon['date'] = datetime.datetime.utcfromtimestamp(
                data_resp['tvalue'])
            dungeon['practice'] = data_resp['practice_mode']

            if data_resp['win_lose'] == 1:
                dungeon['win'] = True
                if 'clear_time' not in data_resp or not isinstance(data_resp['clear_time'], dict):
                    return  # Predator -_-
                time_str = str(data_resp['clear_time']['current_time'])
                _time = {
                    'hour': 0 if int(time_str[:-3]) < 3600 else math.floor(int(time_str[:-3]) / 3600),
                    'minute': 0 if int(time_str[:-3]) < 60 else math.floor(int(time_str[:-3]) / 60),
                    'second': int(time_str[:-3]) if int(time_str[:-3]) < 60 else int(time_str[:-3]) % 60,
                    'microsecond': int(time_str[-3:]) * 1000,
                }
                dungeon['clear_time'] = datetime.time(
                    _time['hour'], _time['minute'], _time['second'], _time['microsecond'])
            else:
                dungeon['win'] = False

            monsters = list()
            # whole info (with runes) is in response data, but by unknown reason sometimes it's a good JSON, sometimes bad
            # good  ->  [Rune, Rune, Rune]
            # bad   ->  instead of list of Rune objects, it has number objects { "5": Rune , "6": Rune, "7": Rune}
            # so, using monster_id from request data, if exists in database
            monsters = Monster.objects.filter(id__in=[m['unit_id'] if not isinstance(
                m['unit_id'], dict) else m['unit_id']['unit_id'] for m in data_req['unit_id_list']])

            obj, _ = DimensionHoleRun.objects.update_or_create(
                id=data_req['battle_key'], defaults=dungeon)
            obj.monsters.set(monsters)
            obj.save()
            logger.debug(
                f"Successfuly created Dimension Hole ({dungeon['dungeon']}) Run for {data_resp['wizard_info']['wizard_id']}")
    except Exception as e:  # to find all exceptions and fix them without breaking the whole app, it is a temporary solution
        log_exception(e, data_resp=data_resp, data_req=data_req)


@shared_task
def handle_wizard_arena_upload_task(data_resp, data_req):
    try:
        with transaction.atomic():
            if data_req['wizard_id'] == data_req['target_wizard_id'] or data_resp['lobby_wizard_log']['page_no'] != 1:
                return
            wizard = {
                'id': data_req['target_wizard_id'],
                'last_update': datetime.datetime.utcfromtimestamp(data_resp['tvalue']),
            }
            wizard, _ = Wizard.objects.update_or_create(
                id=wizard['id'], defaults=wizard, )
            arena_rank = {
                'wizard': wizard,
                'rank': data_resp['lobby_wizard_log']['pvp_best_rating_id'],
            }
            Arena.objects.update_or_create(
                wizard=arena_rank['wizard'], defaults=arena_rank, )
    except Exception as e:
        log_exception(e, data_resp=data_resp, data_req=data_req)
###########################################################


@shared_task
def create_monster_report_by_bot(monster_id):
    base_monster = MonsterBase.objects.get(id=monster_id)

    monsters, hoh_exist, hoh_date, fusion_exist, filename, monsters_runes, monster_family, monsters_artifacts = get_monster_info(
        base_monster)

    try:
        plots, most_common_builds, plot_sets, plot_builds, top_sets, plot_artifact_element_main, plot_artifact_archetype_main, artifact_best = generate_plots(
            monsters, monsters_runes, base_monster, monsters_artifacts, True)
    except KeyError as e:  # no results
        plots = None
        most_common_builds = 'No information given'
        plot_sets = None
        plot_builds = None
        top_sets = None
        plot_artifact_element_main = None
        plot_artifact_archetype_main = None
        artifact_best = None

    context = {
        'base_monster': base_monster,
        'monsters': monsters,
        'family': monster_family,
        'hoh': hoh_exist,
        'hoh_date': hoh_date,
        'fusion': fusion_exist,
        'plots': plots,
        'most_common_builds': most_common_builds,
        'date_update': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'plot_sets': plot_sets,
        'plot_builds': plot_builds,
        'top_sets': top_sets,
        'plot_artifacts_element_main': plot_artifact_element_main,
        'plot_artifacts_archetype_main': plot_artifact_archetype_main,
        'artifact_best': artifact_best,
    }

    html = render_to_string('website/report/report_bot_generate.html', context)

    try:
        html_file = open("website/bot/monsters/" +
                         str(monster_id) + '.html', "w")
        html_file.write(html)
        html_file.close()
        print("[Bot][Periodic Task] Created report about " + str(monster_id))
        return True
    except:
        print("[Bot][Periodic Task] Error has been raised while creating report about " + str(monster_id))
        return False


@shared_task
def generate_bot_reports(monster_id=None):
    # import locally because of circular import
    from .views import create_monster_report_by_bot

    if monster_id:
        monsters_base = [monster_id]
    else:
        monsters_base = list(MonsterBase.objects.filter(~Q(archetype=5)).values_list(
            'id', flat=True))  # archetype=5 -> Material Monsters
        monsters_base.sort()

    g = group(create_monster_report_by_bot.s(monster_id)
              for monster_id in monsters_base)
    g.apply_async()
