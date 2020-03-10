from django import template
from website.models import MonsterBase

register = template.Library()

@register.filter
def get_attribute_avatar(path, monster):
    filename = 'attribute_'
    if type(monster) is MonsterBase:
        filename += monster.get_attribute_display().lower()
    elif type(monster) is str:
        filename += monster.lower()
    else:
        filename += monster.base_monster.get_attribute_display().lower()
    
    return path + filename + '.png'