from django import template

register = template.Library()

@register.filter
def check_skillups(monster):
    skills = [None for _ in range(4)]
    max_skills = monster.base_monster.max_skills
    skilled_up = True
    for i in range(len(monster.skills)):
        if max_skills[i] != monster.skills[i]:
            skilled_up = False
            break
        
    return skilled_up