from django.shortcuts import get_object_or_404, render

from website.models import Wizard, RuneSet, Rune, MonsterFamily, MonsterBase, MonsterSource, Monster, MonsterRep, MonsterHoh, MonsterFusion

# Create your views here.
def specific_rune(request, rune_id):
    rune = get_object_or_404(Rune, id=rune_id)
    context = { 'rune': rune, }

    return render( request, 'website/runes/specific.html', context )