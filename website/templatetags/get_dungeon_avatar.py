from django import template

register = template.Library()

@register.filter
def get_dungeon_avatar(path, dungeon):
    dungeon_name = dungeon
    if type(dungeon) is not str:
        dungeon_name = dungeon.get_dungeon_display()
    return path + 'dungeon_' + dungeon_name.replace('\'', '').replace(' ', '_').lower() + '.png'