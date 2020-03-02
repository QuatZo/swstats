from django import template

register = template.Library()

@register.filter
def rune_grinded_val(stat, zeros=False):
    if stat == None or stat == '' or not stat:
        if zeros:
            return "0"
        return "-"
    if stat[0] and stat[1]:
        return stat[0] + stat[1]
    elif stat[0] and not stat[1]:
        return stat[0]