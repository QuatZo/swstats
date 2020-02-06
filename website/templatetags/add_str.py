from django import template

register = template.Library()

@register.filter
def add_str(arg1, arg2):
    return str(arg1) + str(arg2)