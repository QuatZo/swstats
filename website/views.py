from django.shortcuts import render
from django.http import HttpResponse

from .models import Rune

# Create your views here.

def index(request):
    return HttpResponse(Rune.objects.all())
