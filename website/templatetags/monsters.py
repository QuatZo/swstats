from django import template
from website.models import MonsterBase, Monster, Rune, Artifact

register = template.Library()

@register.filter
def monster_name_from_filename(filename):
    names = filename.replace('_infographic.png', '').split('_')
    names = [name.capitalize() for name in names]
    return ' '.join(names)

@register.filter
def get_star_base_avatar(path, monster):
    filename = 'star_'
    if type(monster) is MonsterBase:
        base_monster = monster
    else:
        base_monster = monster.base_monster

    filename += str(base_monster.awaken)
    
    return path + filename + '.png'

@register.filter
def get_star_avatar(path, monster):
    filename = 'star_'
    if type(monster) is MonsterBase or type(monster) is str:
        return path + filename + '0.png'

    filename += str(monster.base_monster.awaken)
    
    return path + filename + '.png'

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
            filename = filename.replace('-', '_').replace('(', '_').replace(')', '')
    else:
        filename += monster_name.lower().replace(' (', '_').replace(')', '').replace(' ', '')
    
    return path + filename + '.png'

@register.filter
def get_monster(obj, rta=False):
    if isinstance(obj, Rune):
        if rta:
            for monster in obj.equipped_runes_rta.all():
                return monster
        else:
            for monster in obj.equipped_runes.all():
                return monster
    
    if isinstance(obj, Artifact):
        if rta:
            for monster in obj.equipped_artifacts_rta.all():
                return monster
        else:
            for monster in obj.equipped_artifacts.all():
                return monster

    return None

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

@register.filter
def check_skillups(monster):
    max_skills = monster.base_monster.max_skills
    skilled_up = True
    for i in range(len(monster.skills)):
        if max_skills[i] != monster.skills[i]:
            skilled_up = False
            break
        
    return skilled_up

@register.filter
def get_monster_runes_sorted(monster, monsters_runes):
    return monsters_runes[monster.id]

@register.filter
def get_monster_artifacts_sorted(monster, monsters_artifacts):
    return monsters_artifacts[monster.id]