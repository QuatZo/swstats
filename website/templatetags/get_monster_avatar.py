from django import template
from website.models import MonsterBase

register = template.Library()

@register.filter
def get_monster_avatar(path, monster):
    filename = 'monster_'
    if type(monster) is MonsterBase:
        base_monster = monster
    else:
        base_monster = monster.base_monster

    if base_monster.id % 100 > 10:
        if base_monster.id % 100 > 20:
            filename += 'second'
        filename += 'awakened_' + base_monster.name.lower().replace('(2a)', '').replace(' ', '')
        if 'homunculus' in filename:
            filename = filename.replace('-', '_').replace('(', '_').replace(')', '')
    else:
        filename += base_monster.name.lower().replace(' (', '_').replace(')', '').replace(' ', '')
    
    return path + filename + '.png'