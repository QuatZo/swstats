from django import template
from website.models import Monster

register = template.Library()

@register.filter
def get_monster(rune):
    return rune.equipped_runes.first()