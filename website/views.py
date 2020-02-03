from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse

from rest_framework import viewsets, permissions, status

from .models import Wizard, RuneSet, Rune, MonsterFamily, MonsterBase, MonsterSource, Monster, MonsterRep
from .serializers import WizardSerializer, RuneSetSerializer, RuneSerializer, MonsterFamilySerializer, MonsterBaseSerializer, MonsterSourceSerializer, MonsterSerializer, MonsterRepSerializer

# Temporarily here
def calc_efficiency(rune):
    return 2137

# Create your views here.
def specific_rune(request, rune_id):
    rune = get_object_or_404(Rune, id=rune_id)
    context = { 'rune': rune, }

    return render( request, 'website/runes/specific.html', context )

class MonsterFamilyUploadViewSet(viewsets.ViewSet):
    def create(self, request):
        if request.data:
            for family in request.data:
                obj, created = MonsterFamily.objects.update_or_create( id=family['id'], defaults=family, )
            return HttpResponse(status=status.HTTP_201_CREATED)
        
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

class MonsterSourceUploadViewSet(viewsets.ViewSet):
    def create(self, request):
        if request.data:
            for source in request.data:
                obj, created = MonsterSource.objects.update_or_create( id=source['id'], defaults=source, )
            return HttpResponse(status=status.HTTP_201_CREATED)
        
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

class MonsterBaseUploadViewSet(viewsets.ViewSet):
     def create(self, request):
        if request.data:
            for base in request.data:
                monster_base = dict()
                ########################################
                # Monster Base Model
                monster_base['id'] = base['id']
                base['id'] = str(base['id'])
                monster_base['family_id'] = MonsterFamily.objects.get(id=int(base['id'][:-2]))
                monster_base['base_class'] = base['base_class']
                monster_base['name'] = base['name']
                monster_base['attribute'] = int(base['id'][-1])
                monster_base['archetype'] = base['archetype']
                monster_base['max_skills'] = base['max_skills']
                ########################################

                obj, created = MonsterBase.objects.update_or_create( id=base['id'], defaults=monster_base, )
            return HttpResponse(status=status.HTTP_201_CREATED)
        
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

class UploadViewSet(viewsets.ViewSet):
    def create(self, request):
        # prepare dictionaries for every command
        wizard = dict()
        rune = dict()
        monster = dict()

        if request.data:
            if request.data["command"] == "HubUserLogin":
                data = request.data
                print("Starting profile upload for", data['wizard_info']['wizard_name'], "(ID:", data['wizard_info']['wizard_id'], ")")

                temp_wizard = data['wizard_info']
                temp_runes = data['runes']
                for monster in data['unit_list']:
                    for rune in monster['runes']:
                        temp_runes.append(rune)

                ########################################
                # Wizard Model
                wizard['id'] = temp_wizard['wizard_id']
                wizard['mana'] = temp_wizard['wizard_mana']
                wizard['crystals'] = temp_wizard['wizard_crystal']
                wizard['crystals_paid'] = temp_wizard['wizard_crystal_paid']
                wizard['last_login'] = temp_wizard['wizard_last_login']
                wizard['country'] = temp_wizard['wizard_last_country']
                wizard['lang'] = temp_wizard['wizard_last_lang']
                wizard['level'] = temp_wizard['wizard_level']
                wizard['energy'] = temp_wizard['wizard_energy']
                wizard['energy_max'] = temp_wizard['energy_max']
                wizard['arena_wing'] = temp_wizard['arena_energy']
                wizard['glory_point'] = temp_wizard['honor_point']
                wizard['guild_point'] = temp_wizard['guild_point']
                wizard['rta_point'] = temp_wizard['honor_medal']
                wizard['rta_mark'] = temp_wizard['honor_mark']
                wizard['event_coin'] = temp_wizard['event_coin']
                ########################################

                for temp_rune in temp_runes:
                    rune = dict()
                    ########################################
                    # Rune Model
                    rune['id'] = temp_rune['rune_id']
                    rune['user_id'] = Wizard.objects.get(id=temp_rune['wizard_id'])
                    rune['slot'] = temp_rune['slot_no']
                    rune['quality'] = temp_rune['rank']
                    rune['stars'] = temp_rune['class']
                    rune['rune_set'] = RuneSet.objects.get(id=temp_rune['set_id'])
                    rune['upgrade_curr'] = temp_rune['upgrade_curr']
                    rune['base_value'] = temp_rune['base_value']
                    rune['sell_value'] = temp_rune['sell_value']
                    rune['primary'] = temp_rune['pri_eff'][0]
                    rune['primary_value'] = temp_rune['pri_eff'][1]
                    rune['innate'] = temp_rune['prefix_eff'][0]
                    rune['innate_value'] = temp_rune['prefix_eff'][1]
                    rune['substats'] = [sub[0] for sub in temp_rune['sec_eff']]
                    rune['substats_values'] = [sub[1] for sub in temp_rune['sec_eff']]
                    rune['substats_enchants'] = [sub[2] for sub in temp_rune['sec_eff']]
                    rune['substats_grindstones'] = [sub[3] for sub in temp_rune['sec_eff']]
                    rune['quality_original'] = temp_rune['extra']
                    rune['efficiency'] = calc_efficiency(temp_rune)
                    rune['equipped'] = temp_rune['occupied_type'] - 1 # needs more testing
                    ########################################
                    obj, created = Rune.objects.update_or_create( id=rune['id'], defaults=rune, )

                print("After doing what it needs to do, just create_or_update")
                obj, created = Wizard.objects.update_or_create( id=wizard['id'], defaults=wizard, )
            return HttpResponse(status=status.HTTP_201_CREATED)
        
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)