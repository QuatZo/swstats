from django.contrib import admin
from .models import Wizard, RuneSet, Rune, MonsterFamily, MonsterBase, MonsterSource, Monster, MonsterRep, MonsterHoh, MonsterFusion, Deck, WizardBuilding, Building, Arena


class WizardAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'mana', 'crystals', 'crystals_paid', 'last_login', 'country', 'lang', 'level', 'energy', 'energy_max', 'arena_wing', 'glory_point', 'guild_point',
        'rta_point', 'rta_mark', 'event_coin', 'antibot_count', 'raid_level', 'storage_capacity'
    )

class RuneSetAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'amount')

class RuneAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user_id', 'slot', 'quality', 'stars', 'rune_set', 'upgrade_limit', 'upgrade_curr', 'base_value', 'sell_value', 'primary', 'primary_value', 
        'innate', 'innate_value', 'substats', 'substats_values', 'substats_enchants', 'substats_grindstones', 'quality_original', 'efficiency', 'efficiency_max', 'equipped'
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
        'id', 'user_id', 'base_monster', 'level', 'stars', 'hp', 'attack', 'defense', 'speed', 'res', 'acc', 'crit_rate', 'crit_dmg', 'avg_eff', 'skills', 'get_runes',
        'created', 'source', 'transmog', 'storage', 'locked'
    )
    
    filter_horizontal=('runes', )

    def get_runes(self, obj):
        return "\n".join([str(rune) for rune in obj.runes.all()])

class MonsterRepAdmin(admin.ModelAdmin):
    list_display = ( 'id', 'wizard_id', 'monster_id' )

class MonsterHohAdmin(admin.ModelAdmin):
    list_display = ( 'id', 'monster_id', 'date_open', 'date_close' )

class MonsterFusionAdmin(admin.ModelAdmin):
    list_display = ( 'id', 'monster_id', 'cost' )

class DeckAdmin(admin.ModelAdmin):
    list_display = ( 'id', 'wizard_id', 'place', 'number', 'get_monsters', 'leader' )

    def get_monsters(self, obj):
        return "\n".join([str(monster) for monster in obj.monsters.all()])

class BuildingAdmin(admin.ModelAdmin):
    list_display = ( 'id', 'area', 'name' )

class WizardBuildingAdmin(admin.ModelAdmin):
    list_display = ( 'id', 'wizard_id', 'building_id', 'level' )

class ArenaAdmin(admin.ModelAdmin):
    list_display = ( 'id', 'wizard_id', 'wins', 'loses', 'ratio', 'rank', 'def_1', 'def_2', 'def_3', 'def_4')

    def ratio(self, obj):
        return round(obj.wins / obj.loses, 2) if obj.loses > 0 else 0

# Register your models here.
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