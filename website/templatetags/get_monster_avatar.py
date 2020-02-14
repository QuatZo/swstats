from django import template

register = template.Library()

@register.filter
def get_monster_avatar(path, monster):
    filename = 'monster_'
    if monster.base_monster.id % 100 > 10:
        if monster.base_monster.id % 100 > 20:
            filename += 'second'
        filename += 'awakened_' + monster.base_monster.name.lower().replace('(2a)', '').replace(' ', '')
        if 'homunculus' in filename:
            filename = filename.replace('-', '_').replace('(', '_').replace(')', '')
    else:
        filename += monster.base_monster.name.lower().replace(' (', '_').replace(')', '').replace(' ', '')
    
    return path + filename + '.png'