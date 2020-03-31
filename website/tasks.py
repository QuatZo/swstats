from celery import shared_task 
import requests
from django.urls import reverse

@shared_task 
def generate_cache():
    print('Starting generating cache...')
    namespaces = ['home', 'runes', 'monsters', 'decks', 'dungeons', 'homunculus', 'dimhole', 'siege', 'contribute', 'credits']
    for namespace in namespaces:
        requests.get('https://swstats.info' + reverse(namespace))
    print('Ended generating cache...')