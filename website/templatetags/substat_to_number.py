from django import template

register = template.Library()

@register.filter
def substat_to_number(text):
    try:
        text = float(text.replace('+', '').replace('%', ''))
    except ValueError:
        text = 0
    except AttributeError:
        pass
    return text