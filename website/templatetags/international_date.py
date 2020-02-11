from django import template
from datetime import datetime

register = template.Library()

@register.filter
def international_date(date):
    return date.strftime("%Y-%m-%d %H:%M:%S")