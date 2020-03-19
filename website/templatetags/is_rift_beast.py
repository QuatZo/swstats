from django import template

register = template.Library()

@register.filter
def is_rift_beast(dungeon):
    expr = 'Beast'
    if type(dungeon) is not str:
        if expr in dungeon.get_dungeon_display():
            return True
    else:
        if expr in dungeon:
            return True
        
    return False