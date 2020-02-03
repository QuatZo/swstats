from rest_framework import serializers
from .models import Wizard, RuneSet, Rune, MonsterFamily, MonsterBase, MonsterSource, Monster, MonsterRep

class WizardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wizard
        fields = '__all__'

class RuneSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuneSet
        fields = '__all__'

class RuneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rune
        fields = '__all__'

class MonsterFamilySerializer(serializers.ModelSerializer):
    class Meta:
        model = MonsterFamily
        fields = '__all__'

class MonsterBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonsterBase
        fields = '__all__'

class MonsterSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonsterSource
        fields = '__all__'

class MonsterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Monster
        fields = '__all__'

class MonsterRepSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonsterRep
        fields = '__all__'