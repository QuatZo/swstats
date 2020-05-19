from django import template

register = template.Library()

@register.filter
def dungeon_to_div_id(dungeon):
    if type(dungeon) is not str:
        return str(dungeon.get_dungeon_display()).replace('\'', '').replace(' ', '-').lower()
    return dungeon.replace('\'', '').replace(' ', '-').lower()