from django.contrib import admin
from .models import *


class CommandAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'message_type')


class GuildAdmin(admin.ModelAdmin):
    list_display = ('id', 'level', 'members_max', 'members_amount',
                    'gw_best_place', 'gw_best_ranking', 'siege_ranking', 'last_update')


class WizardAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'mana', 'crystals', 'crystals_paid', 'last_login', 'country', 'lang', 'level', 'energy', 'energy_max', 'arena_wing', 'glory_point', 'guild_point',
        'rta_point', 'rta_mark', 'event_coin', 'antibot_count', 'raid_level', 'storage_capacity', 'guild', 'last_update'
    )


class RuneSetAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'amount')


class RuneAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'wizard_id', 'slot', 'quality', 'stars', 'rune_set', 'upgrade_limit', 'upgrade_curr', 'base_value', 'sell_value', 'primary', 'primary_value',
        'innate', 'innate_value', 'sub_hp_flat', 'sub_hp', 'sub_atk_flat', 'sub_atk', 'sub_def_flat', 'sub_def', 'sub_speed', 'sub_crit_rate', 'sub_crit_dmg',
        'sub_res', 'sub_acc', 'quality_original', 'efficiency', 'efficiency_max', 'equipped', 'equipped_rta', 'locked'
    )


class MonsterFamilyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')


class MonsterBaseAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'family', 'base_class', 'name', 'attribute', 'archetype', 'max_skills', 'awaken',
    )


class MonsterSourceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'farmable')


class MonsterAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'wizard_id', 'base_monster', 'level', 'stars', 'hp', 'attack', 'defense', 'speed', 'res', 'acc', 'crit_rate', 'crit_dmg', 'avg_eff', 'avg_eff_artifacts',
        'avg_eff_total', 'eff_hp', 'skills', 'created', 'source', 'transmog', 'storage', 'locked'
    )

    filter_horizontal = ('runes', 'artifacts', 'runes_rta', 'artifacts_rta')


class MonsterRepAdmin(admin.ModelAdmin):
    list_display = ('id', 'wizard_id', 'monster')


class MonsterHohAdmin(admin.ModelAdmin):
    list_display = ('id', 'monster', 'date_open', 'date_close')


class MonsterFusionAdmin(admin.ModelAdmin):
    list_display = ('id', 'monster', 'cost')


class DeckAdmin(admin.ModelAdmin):
    list_display = ('id', 'wizard_id', 'place', 'number',
                    'leader', 'team_runes_eff')


class BuildingAdmin(admin.ModelAdmin):
    list_display = ('id', 'area', 'name')


class WizardBuildingAdmin(admin.ModelAdmin):
    list_display = ('id', 'wizard_id', 'building', 'level')


class ArenaAdmin(admin.ModelAdmin):
    list_display = ('id', 'wizard_id', 'wins', 'loses', 'ratio',
                    'rank', 'def_1', 'def_2', 'def_3', 'def_4')

    def ratio(self, obj):
        if obj.wins and obj.loses:
            return round(obj.wins / obj.loses, 2) if obj.loses > 0 else 0
        return None


class HomunculusSkillAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description', 'depth', 'letter')


class HomunculusBuildAdmin(admin.ModelAdmin):
    list_display = ('id', 'homunculus', 'depth_1', 'depth_2',
                    'depth_3', 'depth_4', 'depth_5')


class WizardHomunculusAdmin(admin.ModelAdmin):
    list_display = ('id', 'wizard_id', 'homunculus', 'build')


class ArtifactAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'wizard_id', 'rtype', 'attribute', 'archetype', 'level', 'primary', 'primary_value', 'substats', 'substats_values',
        'quality', 'quality_original', 'efficiency', 'efficiency_max', 'equipped', 'equipped_rta', 'locked'
    )


# live
class DungeonRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'wizard_id', 'dungeon', 'stage',
                    'clear_time', 'win', 'date')


class RiftDungeonRunAdmin(admin.ModelAdmin):
    list_display = ('battle_key', 'wizard_id', 'dungeon', 'clear_rating', 'monster_1_id', 'monster_2_id', 'monster_3_id', 'monster_4_id',
                    'monster_5_id', 'monster_6_id', 'monster_7_id', 'monster_8_id', 'leader_id', 'dmg_phase_1', 'dmg_phase_glory', 'dmg_phase_2', 'dmg_total', 'date')


class RaidDungeonRunAdmin(admin.ModelAdmin):
    list_display = ('battle_key', 'wizard_id', 'stage', 'win', 'clear_time', 'monster_1_id', 'monster_2_id', 'monster_3_id', 'monster_4_id',
                    'monster_5_id', 'monster_6_id', 'monster_7_id', 'monster_8_id', 'leader_id', 'date')


class SiegeRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'wizard_id', 'leader_id',
                    'win', 'lose', 'ratio', 'last_update', 'full')


class DimensionHoleRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'wizard_id', 'dungeon', 'stage',
                    'clear_time', 'win', 'practice', 'date')


# Register your models here.
admin.site.register(Command, CommandAdmin)

admin.site.register(Guild, GuildAdmin)
admin.site.register(Wizard, WizardAdmin)
admin.site.register(RuneSet, RuneSetAdmin)
admin.site.register(Rune, RuneAdmin)
admin.site.register(MonsterFamily, MonsterFamilyAdmin)
admin.site.register(MonsterBase, MonsterBaseAdmin)
admin.site.register(MonsterSource, MonsterSourceAdmin)
admin.site.register(Monster, MonsterAdmin)
admin.site.register(MonsterRep, MonsterRepAdmin)
admin.site.register(MonsterHoh, MonsterHohAdmin)
admin.site.register(MonsterFusion, MonsterFusionAdmin)
admin.site.register(Deck, DeckAdmin)
admin.site.register(Building, BuildingAdmin)
admin.site.register(WizardBuilding, WizardBuildingAdmin)
admin.site.register(Arena, ArenaAdmin)
admin.site.register(HomunculusSkill, HomunculusSkillAdmin)
admin.site.register(HomunculusBuild, HomunculusBuildAdmin)
admin.site.register(WizardHomunculus, WizardHomunculusAdmin)
admin.site.register(Artifact, ArtifactAdmin)

# live
admin.site.register(DungeonRun, DungeonRunAdmin)
admin.site.register(RiftDungeonRun, RiftDungeonRunAdmin)
admin.site.register(RaidDungeonRun, RaidDungeonRunAdmin)
admin.site.register(SiegeRecord, SiegeRecordAdmin)
admin.site.register(DimensionHoleRun, DimensionHoleRunAdmin)
