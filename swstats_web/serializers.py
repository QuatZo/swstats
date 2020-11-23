from rest_framework import serializers
from website.models import Monster, MonsterBase, MonsterFamily, Rune, RuneSet


class RuneSerializer(serializers.ModelSerializer):
    quality = serializers.CharField(source='get_quality_display')
    quality_original = serializers.CharField(
        source='get_quality_original_display')
    rune_set = serializers.StringRelatedField()
    level = serializers.IntegerField(source='upgrade_curr')
    primary = serializers.CharField(source='get_primary_display')
    innate = serializers.CharField(source='get_innate_display')
    substats = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    ancient = serializers.SerializerMethodField()

    class Meta:
        model = Rune
        fields = [
            'slot', 'quality', 'quality_original', 'stars', 'rune_set', 'level', 'primary',
            'primary_value', 'innate', 'innate_value', 'substats', 'efficiency', 'efficiency_max',
            'equipped', 'equipped_rta', 'locked', 'image', 'ancient'
        ]

    def get_image(self, obj):
        return obj.get_image()

    def get_substats(self, obj):
        return obj.get_substats()

    def get_ancient(self, obj):
        return obj.is_ancient()


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
    runes = RuneSerializer(many=True)
    runes_rta = RuneSerializer(many=True)

    class Meta:
        model = Monster
        fields = [
            'id', 'base_monster', 'level', 'stars', 'hp', 'attack', 'defense', 'speed',
            'res', 'acc', 'crit_rate', 'crit_dmg', 'avg_eff_total', 'eff_hp', 'eff_hp_def_break',
            'skills', 'runes', 'runes_rta', 'artifacts', 'artifacts_rta', 'created', 'image',
        ]

    def get_image(self, obj):
        return obj.get_image()
