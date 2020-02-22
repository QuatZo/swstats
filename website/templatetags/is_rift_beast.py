from django import template

register = template.Library()

@register.filter
def is_rift_beast(dungeon):
    if 'Beast' in dungeon:
        return True
        
    return False