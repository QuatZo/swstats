from django import template

register = template.Library()

@register.filter
def check_text(text):
    if text:
        return "Given recommendation text contains forbidden words/links. We are trying to delete any irrevelant recommendations, which means mostly the ones which contains 'crystal', 'thumb' or 'like' words."
    return text