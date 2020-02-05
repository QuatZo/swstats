from django import template

register = template.Library()

@register.filter
def zip_substats(rune):
    values = [rune.substats_values[i] + rune.substats_grindstones[i] for i in range(len(rune.substats_values))]

    return zip(rune.get_substats_display(), values, rune.substats_enchants, )