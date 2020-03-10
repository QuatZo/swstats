from django import template
from website.models import MonsterBase

register = template.Library()

@register.filter
def get_star_avatar(path, monster):
    filename = 'star_'
    if type(monster) is MonsterBase or type(monster) is str:
        return path + filename + '0.png'

    filename += str(monster.base_monster.awaken)
    
    return path + filename + '.png'