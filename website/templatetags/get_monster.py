from django import template
from website.models import Monster, Rune, Artifact

register = template.Library()

@register.filter
def get_monster(obj):
    if isinstance(obj, Rune):
        for monster in obj.equipped_runes.all():
            return monster
    
    if isinstance(obj, Artifact):
        for monster in obj.equipped_artifacts.all():
            return monster

    return None