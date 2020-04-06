from django import template

register = template.Library()

@register.filter
def monster_name_from_filename(filename):
    names = filename.replace('_infographic.png', '').split('_')
    names = [name.capitalize() for name in names]
    return ' '.join(names)