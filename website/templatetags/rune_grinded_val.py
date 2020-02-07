from django import template

register = template.Library()

@register.filter
def rune_grinded_val(stat):
    if stat == None:
        return "-"
    elif stat[0] and stat[1]:
        return stat[0] + stat[1]
    elif stat[0] and not stat[1]:
        return stat[0]