from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse

from website.tasks import generate_bot_reports

import time


def bot_get_monster_report(request, monster_id):
    return HttpResponse(open('website/bot/monsters/' + str(monster_id) + '.html', 'r').read())

# BOT DEBUG


def bot_debug_get_monster_report(request, monster_id):
    generate_bot_reports.apply(args=[monster_id])
    return HttpResponse(open('website/bot/monsters/' + str(monster_id) + '.html', 'r').read())


def bot_debug_get_all_monster_report(request):
    _ = generate_bot_reports.apply()

    return 200, {}
