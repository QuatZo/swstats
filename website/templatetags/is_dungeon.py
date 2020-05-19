from django import template

register = template.Library()

@register.filter
def is_dungeon(dungeon):
    if type(dungeon.get_dungeon_display()) is not str:
        return False
    return True