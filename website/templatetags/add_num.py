from django import template

register = template.Library()

@register.filter
def add_num(arg1, arg2):
    return arg1 + arg2