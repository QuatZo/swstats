from django import template

register = template.Library()

@register.filter
def get_dungeon_avatar(path, dungeon):    
    return path + 'dungeon_' + dungeon.replace('\'', '').replace(' ', '_').lower() + '.png'