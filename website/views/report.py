from django.http import HttpResponse
from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from django.template.loader import render_to_string

import logging

from website.models import *
from website.serializers import CommandSerializer
from website.exceptions import ProfileDoesNotExist

# Create your views here.
class ReportGeneratorViewSet(viewsets.ViewSet):
    def create(self, request):
        # upload by using ajax, focused on stuff that Desktop App had
        context = { }

        if request.is_ajax():
            data = request.data
            ########################################
            # there will be a report generator
            context = {
                'base_monster': MonsterBase.objects.get(id=data),
                'monsters': Monster.objects.filter(base_monster__id=data)
            }
            ########################################
            html = render_to_string('website/report/report_generate.html', context)
            return HttpResponse(html)

def get_report(request):
    """Return the Report page."""
    context = {
        'base_monsters': MonsterBase.objects.all(), 
    }
    return render( request, 'website/report/report_index.html', context)