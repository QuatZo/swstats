from django.contrib import admin
from .models import Rune, RuneSet


class RuneSetAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'amount')

class RuneAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'slot', 'quality', 'stars', 'rune_set', 'upgrade_limit', 'upgrade_curr', 'base_value', 'sell_value', 'primary', 'primary_value', 
        'innate', 'innate_value', 'substats', 'substats_values', 'substats_grindstones', 'substats_enchants', 'quality_original', 'equipped'
    )


# Register your models here.
admin.site.register(RuneSet, RuneSetAdmin) # Person Admin Page
admin.site.register(Rune, RuneAdmin) # Relationship Admin Page