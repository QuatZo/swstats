from django import template

register = template.Library()

@register.filter
def get_type(arg):
    return arg.__class__.__name__