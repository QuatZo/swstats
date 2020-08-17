from django import template
from website.models import Artifact

register = template.Library()

@register.filter
def parse_artifact_substats_to_table(substats, substats_values):
    sub_texts = list()
    for sub_key, sub_val in zip(substats, substats_values):
        sub_texts.append(Artifact().get_artifact_substat(sub_key).replace('%', f'{sub_val}%'))
        
    return sub_texts