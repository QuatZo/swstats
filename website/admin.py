from django.contrib import admin
from .models import Wizard, RuneSet, Rune, MonsterFamily, MonsterBase, MonsterSource, Monster, MonsterRep, MonsterHoh, MonsterFusion, Deck, WizardBuilding, Building, Arena, HomunculusSkill, WizardHomunculus, Guild, RuneRTA, Item, WizardItem, DungeonRun, RaidBattleKey

class GuildAdmin(admin.ModelAdmin):
    list_display = ('id', 'level', 'members_max', 'members_amount', 'gw_best_place', 'gw_best_ranking', 'last_update')

class WizardAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'mana', 'crystals', 'crystals_paid', 'last_login', 'country', 'lang', 'level', 'energy', 'energy_max', 'arena_wing', 'glory_point', 'guild_point',
        'rta_point', 'rta_mark', 'event_coin', 'antibot_count', 'raid_level', 'storage_capacity', 'guild', 'last_update'
    )

class RuneSetAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'amount')

class RuneAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'wizard', 'slot', 'quality', 'stars', 'rune_set', 'upgrade_limit', 'upgrade_curr', 'base_value', 'sell_value', 'primary', 'primary_value', 
        'innate', 'innate_value', 'sub_hp_flat', 'sub_hp', 'sub_atk_flat', 'sub_atk', 'sub_def_flat', 'sub_def', 'sub_speed', 'sub_crit_rate', 'sub_crit_dmg', 
        'sub_res', 'sub_acc', 'quality_original', 'efficiency', 'efficiency_max', 'equipped', 'locked'
    )

class MonsterFamilyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')


class MonsterBaseAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'family_id', 'base_class', 'name', 'attribute', 'archetype', 'max_skills', 'awaken', 'recommendation_text', 'recommendation_votes'
    )

class MonsterSourceAdmin(admin.ModelAdmin):
    list_display = ( 'id', 'name', 'farmable' )

class MonsterAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'wizard', 'base_monster', 'level', 'stars', 'hp', 'attack', 'defense', 'speed', 'res', 'acc', 'crit_rate', 'crit_dmg', 'avg_eff', 'eff_hp', 'eff_hp_def_break', 
        'skills', 'get_runes', 'created', 'source', 'transmog', 'storage', 'locked'
    )
    
    filter_horizontal=('runes', )

    def get_runes(self, obj):
        return "\n".join([str(rune) for rune in obj.runes.all()])

class MonsterRepAdmin(admin.ModelAdmin):
    list_display = ( 'id', 'wizard', 'monster' )

class MonsterHohAdmin(admin.ModelAdmin):
    list_display = ( 'id', 'monster', 'date_open', 'date_close' )

class MonsterFusionAdmin(admin.ModelAdmin):
    list_display = ( 'id', 'monster', 'cost' )

class DeckAdmin(admin.ModelAdmin):
    list_display = ( 'id', 'wizard', 'place', 'number', 'get_monsters', 'leader', 'team_runes_eff' )

    def get_monsters(self, obj):
        return "\n".join([str(monster) for monster in obj.monsters.all()])

class BuildingAdmin(admin.ModelAdmin):
    list_display = ( 'id', 'area', 'name' )

class WizardBuildingAdmin(admin.ModelAdmin):
    list_display = ( 'id', 'wizard', 'building', 'level' )

class ArenaAdmin(admin.ModelAdmin):
    list_display = ( 'id', 'wizard', 'wins', 'loses', 'ratio', 'rank', 'def_1', 'def_2', 'def_3', 'def_4')

    def ratio(self, obj):
        return round(obj.wins / obj.loses, 2) if obj.loses > 0 else 0

class HomunculusSkillAdmin(admin.ModelAdmin):
    list_display = ( 'id', 'name', 'description', 'depth' )
    
class WizardHomunculusAdmin(admin.ModelAdmin):
    list_display = ( 'id', 'wizard', 'homunculus', 'skill_1', 'skill_1_plus', 'skill_2', 'skill_2_plus', 'skill_3' )

class RuneRTAAdmin(admin.ModelAdmin):
    list_display = ( 'id', 'monster', 'rune' )

class ItemAdmin(admin.ModelAdmin):
    list_display = ( 'id', 'item_id', 'item_type', 'name')

class WizardItemAdmin(admin.ModelAdmin):
    list_display = ( 'id', 'wizard', 'master_item', 'quantity' )

# live
class DungeonRunAdmin(admin.ModelAdmin):
    list_display = ( 'id', 'wizard', 'dungeon', 'stage', 'clear_time', 'get_monsters', 'win', 'date' )

    def get_monsters(self, obj):
        return "\n".join([str(monster) for monster in obj.monsters.all()])

class RaidBattleKeyAdmin(admin.ModelAdmin):
    list_display = ( 'battle_key', 'stage' )


# Register your models here.
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
admin.site.register(WizardHomunculus, WizardHomunculusAdmin)
admin.site.register(RuneRTA, RuneRTAAdmin)
admin.site.register(Item, ItemAdmin)
admin.site.register(WizardItem, WizardItemAdmin)

# live
admin.site.register(DungeonRun, DungeonRunAdmin)
admin.site.register(RaidBattleKey, RaidBattleKeyAdmin)