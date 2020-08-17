from django import template

register = template.Library()

@register.filter
def dungeon_to_div_id(dungeon):
    if type(dungeon) is not str:
        return str(dungeon.get_dungeon_display()).replace('\'', '').replace(' ', '-').lower()
    return dungeon.replace('\'', '').replace(' ', '-').lower()

@register.filter
def get_dungeon_avatar(path, dungeon):
    dungeon_name = dungeon
    if type(dungeon) is not str:
        dungeon_name = str(dungeon.get_dungeon_display())
    return path + 'dungeon_' + dungeon_name.replace('\'', '').replace(' ', '_').lower() + '.png'


@register.filter
def is_dungeon(dungeon):
    if type(dungeon.get_dungeon_display()) is not str:
        return False
    return True

@register.filter
def is_rift_beast(dungeon):
    expr = 'Beast'
    if type(dungeon) is not str:
        if expr in str(dungeon.get_dungeon_display()):
            return True
    else:
        if expr in dungeon:
            return True
        
    return False