from django.shortcuts import get_object_or_404, render
from django.db.models import F

from website.models import Wizard, RuneSet, Rune, MonsterFamily, MonsterBase, MonsterSource, Monster, MonsterRep, MonsterHoh, MonsterFusion


# Create your views here.
def get_homepage(request):
    runes = Rune.objects.all()
    monsters = Monster.objects.all()
    rune_best = runes.order_by('-efficiency').first()
    rune_equipped = Rune.objects.filter(equipped=True).count()
    monster_best = monsters.order_by('-avg_eff').first()
    monster_cdmg = monsters.order_by('-crit_dmg').first()

    MESSAGES = [
        {
            'id': 1,
            'title': 'Highest rune efficiency',
            'text': f'The most efficient rune stored in database has {rune_best.efficiency if rune_best else 0}% efficiency.',
            'arg': rune_best.id if rune_best else 0,
        },
        {
            'id': 2,
            'title': 'Equipped runes',
            'text': f'From {runes.count()} runes in database, only {rune_equipped} are equipped. it gives us {round(rune_equipped / runes.count() * 100, 2) if runes.count() else 0}% \'useless\' runes.',
        },
        {
            'id': 3,
            'title': 'Highest average efficiency',
            'text': f'{str(monster_best)} has the highest average efficiency, amounting to {monster_best.avg_eff if monster_best else 0}%',
            'arg': monster_best.id if monster_best else 0,
        },
        {
            'id': 4,
            'title': 'Highest critical damage value',
            'text': f'Highest Critical Damage value has {str(monster_cdmg)} with an amazing {monster_cdmg.crit_dmg if monster_cdmg else 0}%',
            'arg': monster_cdmg.id if monster_best else 0,
        },
    ]

    context = {
        'messages': MESSAGES,
    }

    return render( request, 'website/index.html', context )

def get_runes(request):
    runes = Rune.objects.all().order_by('-efficiency')
    amount = min(100, runes.count())
    runes = runes[:amount]

    fastest_runes = Rune.objects.all().order_by(F('sub_speed').desc(nulls_last=True))
    fastest_amount = min(100, fastest_runes.count())
    fastest_runes = fastest_runes[:fastest_amount]

    context = {
        'amount': amount,
        'runes': runes,
        'fastest_runes': fastest_runes,
        'fastest_amount': fastest_amount,
    }

    return render( request, 'website/runes/index.html', context)


def get_specific_rune(request, rune_id):
    rune = get_object_or_404(Rune, id=rune_id)
    context = { 'rune': rune, }

    return render( request, 'website/runes/specific.html', context )

