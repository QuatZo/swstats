from django import template

register = template.Library()

@register.filter
def add_reverse_str(arg1, arg2):
    if arg1 == "":
        return arg1
    return str(arg2) + str(arg1)