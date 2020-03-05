from django import template
from website.models import MonsterBase

register = template.Library()

@register.filter
def get_star_base_avatar(path, monster):
    filename = 'star_'
    if type(monster) is MonsterBase:
        base_monster = monster
    else:
        base_monster = monster.base_monster

    filename += str(base_monster.awaken)
    
    return path + filename + '.png'