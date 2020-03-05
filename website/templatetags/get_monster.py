from django import template
from website.models import Monster

register = template.Library()

@register.filter
def get_monster(rune):
    for monster in rune.equipped_runes.all():
        return monster