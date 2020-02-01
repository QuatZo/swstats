from django.contrib import admin
from .models import Rune, RuneSet, Monster, Wizard


class WizardAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'mana', 'crystals', 'last_login', 'country', 'lang', 'level', 'energy', 'energy_max', 'arena_wing', 'glory_point', 'guild_point',
        'rta_point', 'event_coin'
    )

class RuneSetAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'amount')

class RuneAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user_id', 'slot', 'quality', 'stars', 'rune_set', 'upgrade_limit', 'upgrade_curr', 'base_value', 'sell_value', 'primary', 'primary_value', 
        'innate', 'innate_value', 'substats', 'substats_values', 'substats_grindstones', 'substats_enchants', 'quality_original', 'equipped'
    )

class MonsterAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user_id', 'parent_id', 'level', 'stars', 'con', 'attack', 'defense', 'speed', 'res', 'acc', 'crit_rate', 'crit_dmg', 'get_runes', 'attribute',
        'awaken', 'created', 'storage', 'rep'
    )
    
    filter_horizontal=('runes', )

    def get_runes(self, obj):
        return "\n".join([str(rune) for rune in obj.runes.all()])

# Register your models here.
admin.site.register(Wizard, WizardAdmin)
admin.site.register(RuneSet, RuneSetAdmin)
admin.site.register(Rune, RuneAdmin)
admin.site.register(Monster, MonsterAdmin)