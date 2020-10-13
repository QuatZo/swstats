from django import template
from website.models import MonsterBase

import uuid
import random

register = template.Library()


@register.filter
def val_minus_one(val):
    return val - 1


@register.filter
def to_list(arg):
    return [arg]


@register.filter
def random_id(ids):
    return random.choice(ids)


@register.filter
def is_active(path, url):
    if (url + '.') in path:
        return path[:-4] + '_active.svg'
    return path


@register.filter
def international_date(date):
    return date.strftime("%Y-%m-%d")


@register.filter
def get_type(arg):
    return arg.__class__.__name__


@register.filter
def concat_arrays(a1, a2):
    # make sure these are arrays, in case of getting QuerySets
    return list(a1) + list(a2)


@register.filter
def add_str(arg1, arg2):
    return str(arg1) + str(arg2)


@register.filter
def add_reverse_str(arg1, arg2):
    if arg1 == "":
        return arg1
    return str(arg2) + str(arg1)


@register.filter
def add_num(arg1, arg2):
    return arg1 + arg2


@register.filter
def space_to_(arg1):
    return arg1.replace(' ', '_')


@register.filter
def randomize(val):
    if isinstance(val, str):
        return
    return val * uuid.uuid4().int
