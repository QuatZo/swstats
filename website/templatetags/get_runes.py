from django import template

register = template.Library()

@register.filter
def get_runes(monsters):
    runes = list()

    for monster in monsters:
        for rune in monster.runes.all():
            runes.append(rune)
    
    return runes