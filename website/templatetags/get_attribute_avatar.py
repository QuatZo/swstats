from django import template
from website.models import MonsterBase

register = template.Library()

@register.filter
def get_attribute_avatar(path, monster):
    filename = 'attribute_'
    if type(monster) is MonsterBase:
        base_monster = monster
    else:
        base_monster = monster.base_monster

    filename += base_monster.get_attribute_display().lower()
    
    return path + filename + '.png'