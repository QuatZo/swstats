from django import template

register = template.Library()

@register.filter
def concat_arrays(a1, a2):
    return list(a1) + list(a2) # make sure these are arrays, in case of getting QuerySets