from django import template

register = template.Library()

@register.filter
def check_skillups(monster):
    skills = [None for _ in range(4)]
    max_skills = monster.base_monster.max_skills
    for i in range(len(monster.skills)):
        skills[i] = True if max_skills[i] == monster.skills[i] else f'{monster.skills[i]}/{max_skills[i]}'  
        
    return skills