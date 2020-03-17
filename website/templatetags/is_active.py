from django import template

register = template.Library()

@register.filter
def is_active(path, url):
    if (url + '.') in path:
        return path[:-4] + '_active.svg'
    return path