from rest_framework import serializers
from .models import Command, Monster, Rune, Artifact, MonsterBase, MonsterFamily


class CommandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Command
        fields = '__all__'


class RuneSerializer(serializers.ModelSerializer):
    quality = serializers.CharField(source='get_quality_display')
    quality_original = serializers.CharField(
        source='get_quality_original_display')
    rune_set = serializers.CharField(source='rune_set.name')
    primary = serializers.CharField(source='get_primary_display')
    innate = serializers.CharField(source='get_innate_display')
    stars = serializers.IntegerField(source='get_stars_display')

    class Meta:
        model = Rune
        fields = (
            'id', 'slot', 'rune_set', 'quality', 'quality_original', 'stars', 'is_ancient', 'upgrade_curr', 'primary', 'primary_value', 'innate', 'innate_value',
            'efficiency', 'efficiency_max', 'equipped', 'equipped_rta', 'locked', 'sub_hp_flat', 'sub_hp', 'sub_atk_flat', 'sub_atk', 'sub_def_flat',
            'sub_def', 'sub_speed', 'sub_crit_rate', 'sub_crit_dmg', 'sub_res', 'sub_acc',
        )


class ArtifactSerializer(serializers.ModelSerializer):
    rtype = serializers.CharField(source='get_rtype_display')
    archetype = serializers.CharField(source='get_archetype_display')
    attribute = serializers.CharField(source='get_attribute_display')
    primary = serializers.CharField(source='get_primary_display')
    quality = serializers.CharField(source='get_quality_display')
    quality_original = serializers.CharField(
        source='get_quality_original_display')
    substats = serializers.ListField(source='get_substats_display')

    class Meta:
        model = Artifact
        fields = (
            'id', 'rtype', 'attribute', 'archetype', 'level', 'primary', 'primary_value', 'quality', 'quality_original',
            'efficiency', 'efficiency_max', 'equipped', 'equipped_rta', 'locked', 'substats', 'substats_values',
        )


class MonsterBaseSerializer(serializers.ModelSerializer):
    attribute = serializers.CharField(source='get_attribute_display')
    archetype = serializers.CharField(source='get_archetype_display')
    awaken = serializers.CharField(source='get_awaken_display')
    family = serializers.CharField(source='family.name')

    class Meta:
        model = MonsterBase
        fields = ('id', 'base_class', 'name', 'family',
                  'attribute', 'archetype', 'max_skills', 'awaken',)


class MonsterSerializer(serializers.ModelSerializer):
    runes = RuneSerializer(many=True)
    runes_rta = RuneSerializer(many=True)
    artifacts = ArtifactSerializer(many=True)
    artifacts_rta = ArtifactSerializer(many=True)
    base_monster = MonsterBaseSerializer()

    class Meta:
        model = Monster
        fields = (
            'id', 'base_monster', 'level', 'stars', 'hp', 'attack', 'defense', 'speed', 'res', 'acc', 'crit_rate', 'crit_dmg',
            'eff_hp', 'eff_hp_def_break', 'avg_eff', 'avg_eff_artifacts', 'avg_eff_total', 'skills', 'created', 'transmog',
            'locked', 'storage', 'runes', 'artifacts', 'runes_rta', 'artifacts_rta',
        )
