from django import template

register = template.Library()

@register.filter
def to_list(arg):
    return [arg]