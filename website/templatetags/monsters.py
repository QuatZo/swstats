from django import template
from website.models import MonsterBase, Monster, Rune, Artifact

register = template.Library()


@register.filter
def monster_name_from_filename(filename):
    names = filename.replace('_infographic.png', '').split('_')
    names = [name.capitalize() for name in names]
    return ' '.join(names)


@register.filter
def get_monster_avatar(path, monster):
    filename = 'monster_'
    if type(monster) is MonsterBase:
        base_monster = monster
    else:
        base_monster = monster.base_monster

    monster_id = base_monster.id
    monster_name = base_monster.name

    if monster_id % 100 > 10:
        if monster_id % 100 > 20:
            filename += 'second'
        filename += 'awakened_' + monster_name.lower().replace('(2a)', '').replace(' ', '')
        if 'homunculus' in filename:
            filename = filename.replace(
                '-', '_').replace('(', '_').replace(')', '')
    else:
        filename += monster_name.lower().replace(' (', '_').replace(')', '').replace(' ', '')

    return path + filename + '.png'
