from django.shortcuts import get_object_or_404, render

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
            'text': f'The most efficient rune stored in database has {rune_best.efficiency}% efficiency.',
            'arg': rune_best.id,
        },
        {
            'id': 2,
            'title': 'Equipped runes',
            'text': f'From {runes.count()} runes in database, only {rune_equipped} are equipped. it gives us {round(rune_equipped / runes.count() * 100, 2)}% \'useless\' runes.',
        },
        {
            'id': 3,
            'title': 'Highest average efficiency',
            'text': f'{str(monster_best)} has the highest average efficiency, amounting to {monster_best.avg_eff}%',
            'arg': monster_best.id,
        },
        {
            'id': 4,
            'title': 'Highest critical damage value',
            'text': f'Highest Critical Damage value has {str(monster_cdmg)} with an amazing {monster_cdmg.crit_dmg}%',
            'arg': monster_best.id,
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

    fastest_runes = Rune.objects.filter(substats__contains=[8]).order_by('-substats_values') # doesn't work as intended, currentyl a placeholder for template
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

