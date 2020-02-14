from django import template
from website.models import Monster

register = template.Library()

@register.filter
def get_monster(rune):
    return Monster.objects.all().get(runes=rune.id)