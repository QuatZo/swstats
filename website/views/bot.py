from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse

def bot_get_monster_report(request, monster_id):
    return HttpResponse(open('website/bot/monsters/' + str(monster_id) + '.html', 'r').read())