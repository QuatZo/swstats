from django import template

register = template.Library()

@register.filter
def dungeon_to_div_id(dungeon):
    return dungeon.replace('\'', '').replace(' ', '-').lower()