from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response

from swstats_web.permissions import IsSwstatsWeb
from website.models import Monster, Rune, Artifact, DungeonRun
# Create your views here.


class Homepage(APIView):
    permission_classes = [IsSwstatsWeb, ]

    def get(self, request, format=None):
        cards = [
            {
                "id": 1,
                "animated": False,
                "format": "string",
                "w": 3,  # 1-12, card width
                "title": "Summoners War Statistics Web",
                "desc": "Summoners War Statistics Web is a website which stores, analyse and shows in a friendly way contributors data but also implements the most important features from Summoners War Statistics Windows App which had been discontinued because of technology limits.",
            },
            {
                "id": 2,
                "animated": False,
                "format": "string",
                "w": 3,  # 1-12, card width
                "title": "Data Logs",
                "desc": "In Data Logs Section you can find analysis, charts, tables and reports based on Contributors data. Every data used in Data Logs Section is being collected annonymously by using website built-in Upload Functionality (together with Rank & Compare) or by using SWEX Plugin. More information in Contribute page.",
            },
            {
                "id": 3,
                "animated": False,
                "format": "string",
                "w": 3,
                "title": "Personal",
                "desc": "In Personal Section you can find towers & flags calculator, 2A  calculator and graphic representation of your profile: Summoner, Monsters (with details), Runes (with details), Guild, Guild members activity, Friends activity. Data sent through Personal Section IS NOT stored in our database.",
            },
            {
                "id": 4,
                "animated": False,
                "format": "string",
                "w": 3,
                "title": "I don't want my data to be here",
                "desc": "I can assure you that no user will be able to tell if specific monster, rune, artifact or dungeon run is yours or not. However, if you want your data to be deleted, please contact me through Reddit and we will see what can be done. Be prepare to give me JSON file, in order to blacklist it."
            },
            {
                "id": 5,
                "animated": True,
                "format": "number",
                "precision": 0,
                "w": 2,
                "title": "Monsters",
                "desc": Monster.objects.all().count(),
            },
            {
                "id": 6,
                "animated": True,
                "format": "number",
                "precision": 0,
                "w": 2,
                "title": "Runes",
                "desc": Rune.objects.all().count(),
            },
            {
                "id": 7,
                "animated": True,
                "format": "number",
                "precision": 0,
                "w": 2,
                "title": "Artifacts",
                "desc": Artifact.objects.all().count(),
            },
            {
                "id": 8,
                "animated": True,
                "format": "percentage",
                "precision": 2,
                "w": 3,
                "title": "Most Efficient Rune",
                "desc": Rune.objects.order_by('-efficiency').first().efficiency,
            },
            {
                "id": 9,
                "animated": True,
                "format": "percentage",
                "precision": 0,
                "w": 3,
                "title": "Highest Crit Damage",
                "desc": Monster.objects.order_by('-crit_dmg').first().crit_dmg,
            },
            {
                "id": 10,
                "animated": True,
                "format": "number",
                "precision": 0,
                "w": 2,
                "title": "Highest Speed",
                "desc": Monster.objects.order_by('-speed').first().speed,
            },
            {
                "id": 11,
                "animated": True,
                "format": "seconds",
                "w": 2,
                "title": "Fastest GB12",
                "desc": DungeonRun.objects.filter(win=True, dungeon=8001, stage=12).order_by('clear_time').first().clear_time.total_seconds(),
            },
            {
                "id": 12,
                "animated": True,
                "format": "seconds",
                "w": 2,
                "title": "Fastest DB12",
                "desc": DungeonRun.objects.filter(win=True, dungeon=9001, stage=12).order_by('clear_time').first().clear_time.total_seconds(),
            },
            {
                "id": 13,
                "animated": True,
                "format": "seconds",
                "w": 2,
                "title": "Fastest NB12",
                "desc": DungeonRun.objects.filter(win=True, dungeon=6001, stage=12).order_by('clear_time').first().clear_time.total_seconds(),
            },
            {
                "id": 14,
                "animated": True,
                "format": "seconds",
                "w": 2,
                "title": "Fastest SB10",
                "desc": DungeonRun.objects.filter(win=True, dungeon=9501, stage=10).order_by('clear_time').first().clear_time.total_seconds(),
            },
            {
                "id": 15,
                "animated": True,
                "format": "seconds",
                "w": 2,
                "title": "Fastest PB10",
                "desc": DungeonRun.objects.filter(win=True, dungeon=9502, stage=10).order_by('clear_time').first().clear_time.total_seconds(),
            },

        ]

        return Response(cards)
