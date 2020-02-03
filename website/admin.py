from django.contrib import admin
from .models import Wizard, RuneSet, Rune, MonsterFamily, MonsterBase, MonsterSource, Monster, MonsterRep


class WizardAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'mana', 'crystals', 'crystals_paid', 'last_login', 'country', 'lang', 'level', 'energy', 'energy_max', 'arena_wing', 'glory_point', 'guild_point',
        'rta_point', 'rta_mark', 'event_coin'
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
        'created', 'storage', 'source'
    )
    
    filter_horizontal=('runes', )

    def get_runes(self, obj):
        return "\n".join([str(rune) for rune in obj.runes.all()])

class MonsterRepAdmin(admin.ModelAdmin):
    list_display = ( 'id', 'wizard_id', 'monster_id' )

# Register your models here.
admin.site.register(Wizard, WizardAdmin)
admin.site.register(RuneSet, RuneSetAdmin)
admin.site.register(Rune, RuneAdmin)
admin.site.register(MonsterFamily, MonsterFamilyAdmin)
admin.site.register(MonsterBase, MonsterBaseAdmin)
admin.site.register(MonsterSource, MonsterSourceAdmin)
admin.site.register(Monster, MonsterAdmin)
admin.site.register(MonsterRep, MonsterRepAdmin)