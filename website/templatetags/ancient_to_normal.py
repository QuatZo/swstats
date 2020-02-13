from django import template

register = template.Library()

@register.filter
def ancient_to_normal(quality):
    return quality.replace('Ancient ', '')