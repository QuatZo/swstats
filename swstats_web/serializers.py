from rest_framework import serializers
from website.models import Monster, MonsterBase, MonsterFamily


class MonsterBaseSerializer(serializers.ModelSerializer):
    family = serializers.StringRelatedField()
    attribute = serializers.CharField(source='get_attribute_display')
    archetype = serializers.CharField(source='get_archetype_display')
    awaken = serializers.CharField(source='get_awaken_display')

    class Meta:
        model = MonsterBase
        fields = [
            'family', 'base_class', 'name', 'attribute', 'archetype', 'max_skills', 'awaken',
        ]


class MonsterSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    base_monster = MonsterBaseSerializer()

    class Meta:
        model = Monster
        fields = [
            'id', 'base_monster', 'level', 'stars', 'hp', 'attack', 'defense', 'speed',
            'res', 'acc', 'crit_rate', 'crit_dmg', 'avg_eff_total', 'eff_hp', 'eff_hp_def_break',
            'skills', 'runes', 'runes_rta', 'artifacts', 'artifacts_rta', 'created', 'image',
        ]

    def get_image(self, obj):
        return obj.get_image()
