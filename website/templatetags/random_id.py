from django import template
from website.models import MonsterBase

import random

register = template.Library()

@register.filter
def random_id(ids):
    return random.choice(ids)