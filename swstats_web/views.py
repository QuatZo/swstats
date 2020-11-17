from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response

from swstats_web.permissions import IsSwstatsWeb
from website.models import Monster
# Create your views here.

class Homepage(APIView):
    permission_classes = [IsSwstatsWeb, ]

    def get(self, request, format=None):
        return Response(Monster.objects.all().count())