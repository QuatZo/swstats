# Generated by Django 3.0.3 on 2020-02-29 17:27

import django.contrib.postgres.fields
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Building',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False, unique=True)),
                ('area', models.IntegerField(choices=[(0, 'Arena'), (1, 'Guild')])),
                ('name', models.CharField(max_length=50)),
            ],
            options={
                'ordering': ['area', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Command',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128)),
                ('message_type', models.IntegerField(choices=[(1, 'Request'), (2, 'Response'), (3, 'Both')])),
            ],
        ),
        migrations.CreateModel(
            name='Guild',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False, unique=True)),
                ('level', models.SmallIntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(30)])),
                ('members_amount', models.SmallIntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(30)])),
                ('gw_best_place', models.IntegerField()),
                ('gw_best_ranking', models.IntegerField(choices=[(1011, 'Challenger'), (2011, 'Fighter I'), (2012, 'Fighter II'), (2013, 'Fighter III'), (3011, 'Conqueror I'), (3012, 'Conqueror II'), (3013, 'Conqueror III'), (4011, 'Guardian I'), (4012, 'Guardian II'), (4013, 'Guardian III'), (5011, 'Legend')])),
                ('siege_ranking', models.IntegerField(blank=True, choices=[(1001, 'Challenger'), (2001, 'Fighter I'), (2002, 'Fighter II'), (2003, 'Fighter III'), (3001, 'Conqueror I'), (3002, 'Conqueror II'), (3003, 'Conqueror III'), (4001, 'Guardian I'), (4002, 'Guardian II'), (4003, 'Guardian III'), (5001, 'Legend')], null=True)),
                ('last_update', models.DateTimeField()),
            ],
            options={
                'ordering': ['-gw_best_place', '-gw_best_ranking', '-level', '-members_amount', 'id'],
            },
        ),
        migrations.CreateModel(
            name='HomunculusBuild',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='HomunculusSkill',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False, unique=True)),
                ('name', models.CharField(max_length=50)),
                ('description', models.CharField(max_length=512)),
                ('depth', models.SmallIntegerField()),
                ('letter', models.CharField(max_length=1, null=True)),
            ],
            options={
                'ordering': ['depth', 'id'],
            },
        ),
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_id', models.IntegerField()),
                ('item_type', models.SmallIntegerField(choices=[(6, '?'), (9, 'Scroll'), (11, 'Essence'), (12, 'Monster Pieces'), (15, '??'), (16, '???'), (19, '????'), (20, '????????'), (29, 'Crafting Material'), (37, '?????'), (57, '??????'), (58, '???????'), (61, 'Evolve Material')])),
                ('name', models.CharField(max_length=50)),
            ],
            options={
                'ordering': ['item_type', 'item_id'],
            },
        ),
        migrations.CreateModel(
            name='Monster',
            fields=[
                ('id', models.BigIntegerField(primary_key=True, serialize=False, unique=True)),
                ('level', models.SmallIntegerField()),
                ('stars', models.SmallIntegerField()),
                ('hp', models.IntegerField()),
                ('attack', models.IntegerField()),
                ('defense', models.IntegerField()),
                ('speed', models.IntegerField()),
                ('res', models.IntegerField()),
                ('acc', models.IntegerField()),
                ('crit_rate', models.IntegerField()),
                ('crit_dmg', models.IntegerField()),
                ('avg_eff', models.FloatField(validators=[django.core.validators.MinValueValidator(0.0)])),
                ('eff_hp', models.IntegerField(validators=[django.core.validators.MinValueValidator(0.0)])),
                ('eff_hp_def_break', models.IntegerField(validators=[django.core.validators.MinValueValidator(0.0)])),
                ('skills', django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(), size=None)),
                ('created', models.DateTimeField()),
                ('transmog', models.BooleanField()),
                ('locked', models.BooleanField()),
                ('storage', models.BooleanField()),
            ],
            options={
                'ordering': ['-stars', '-level', 'base_monster'],
            },
        ),
        migrations.CreateModel(
            name='MonsterBase',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False, unique=True)),
                ('base_class', models.SmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(6)])),
                ('name', models.CharField(max_length=50)),
                ('attribute', models.SmallIntegerField(choices=[(1, 'Water'), (2, 'Fire'), (3, 'Wind'), (4, 'Light'), (5, 'Dark')])),
                ('archetype', models.SmallIntegerField(choices=[(0, 'None'), (1, 'Attack'), (2, 'Defense'), (3, 'HP'), (4, 'Support'), (5, 'Material')])),
                ('max_skills', django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(), size=None)),
                ('awaken', models.SmallIntegerField(choices=[(0, 'Unawakened'), (1, 'Awakened'), (2, '2A')])),
                ('recommendation_text', models.CharField(blank=True, max_length=512, null=True)),
                ('recommendation_votes', models.IntegerField(blank=True, default=0)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='MonsterFamily',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False, unique=True)),
                ('name', models.CharField(max_length=30)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='MonsterSource',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False, unique=True)),
                ('name', models.CharField(max_length=30)),
                ('farmable', models.BooleanField()),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='RaidBattleKey',
            fields=[
                ('battle_key', models.BigIntegerField(primary_key=True, serialize=False, unique=True)),
                ('stage', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='Rune',
            fields=[
                ('id', models.BigIntegerField(primary_key=True, serialize=False, unique=True)),
                ('slot', models.SmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(6)])),
                ('quality', models.SmallIntegerField(choices=[(0, 'Unknown'), (1, 'Common'), (2, 'Magic'), (3, 'Rare'), (4, 'Hero'), (5, 'Legend'), (11, 'Ancient Common'), (12, 'Ancient Magic'), (13, 'Ancient Rare'), (14, 'Ancient Hero'), (15, 'Ancient Legend')])),
                ('stars', models.SmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(6)])),
                ('upgrade_curr', models.SmallIntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(15)])),
                ('base_value', models.IntegerField()),
                ('sell_value', models.IntegerField()),
                ('primary', models.SmallIntegerField(choices=[(1, 'HP+'), (2, 'HP%'), (3, 'ATK+'), (4, 'ATK%'), (5, 'DEF+'), (6, 'DEF%'), (8, 'SPD'), (9, 'CRate%'), (10, 'CDmg%'), (11, 'RES%'), (12, 'ACC%')])),
                ('primary_value', models.IntegerField()),
                ('innate', models.SmallIntegerField(choices=[(1, 'HP+'), (2, 'HP%'), (3, 'ATK+'), (4, 'ATK%'), (5, 'DEF+'), (6, 'DEF%'), (8, 'SPD'), (9, 'CRate%'), (10, 'CDmg%'), (11, 'RES%'), (12, 'ACC%')])),
                ('innate_value', models.IntegerField()),
                ('sub_hp_flat', django.contrib.postgres.fields.ArrayField(base_field=models.SmallIntegerField(), blank=True, null=True, size=None)),
                ('sub_hp', django.contrib.postgres.fields.ArrayField(base_field=models.SmallIntegerField(), blank=True, null=True, size=None)),
                ('sub_atk_flat', django.contrib.postgres.fields.ArrayField(base_field=models.SmallIntegerField(), blank=True, null=True, size=None)),
                ('sub_atk', django.contrib.postgres.fields.ArrayField(base_field=models.SmallIntegerField(), blank=True, null=True, size=None)),
                ('sub_def_flat', django.contrib.postgres.fields.ArrayField(base_field=models.SmallIntegerField(), blank=True, null=True, size=None)),
                ('sub_def', django.contrib.postgres.fields.ArrayField(base_field=models.SmallIntegerField(), blank=True, null=True, size=None)),
                ('sub_speed', django.contrib.postgres.fields.ArrayField(base_field=models.SmallIntegerField(), blank=True, null=True, size=None)),
                ('sub_crit_rate', django.contrib.postgres.fields.ArrayField(base_field=models.SmallIntegerField(), blank=True, null=True, size=None)),
                ('sub_crit_dmg', django.contrib.postgres.fields.ArrayField(base_field=models.SmallIntegerField(), blank=True, null=True, size=None)),
                ('sub_res', django.contrib.postgres.fields.ArrayField(base_field=models.SmallIntegerField(), blank=True, null=True, size=None)),
                ('sub_acc', django.contrib.postgres.fields.ArrayField(base_field=models.SmallIntegerField(), blank=True, null=True, size=None)),
                ('quality_original', models.SmallIntegerField(choices=[(0, 'Unknown'), (1, 'Common'), (2, 'Magic'), (3, 'Rare'), (4, 'Hero'), (5, 'Legend'), (11, 'Ancient Common'), (12, 'Ancient Magic'), (13, 'Ancient Rare'), (14, 'Ancient Hero'), (15, 'Ancient Legend')])),
                ('efficiency', models.FloatField(validators=[django.core.validators.MinValueValidator(0.0)])),
                ('efficiency_max', models.FloatField(validators=[django.core.validators.MinValueValidator(0.0)])),
                ('equipped', models.BooleanField()),
                ('locked', models.BooleanField()),
            ],
            options={
                'ordering': ['slot', 'rune_set', '-efficiency', '-stars'],
            },
        ),
        migrations.CreateModel(
            name='RuneSet',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False, unique=True)),
                ('name', models.CharField(max_length=30)),
                ('amount', models.IntegerField()),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Wizard',
            fields=[
                ('id', models.BigIntegerField(primary_key=True, serialize=False, unique=True)),
                ('mana', models.BigIntegerField(blank=True, default=None, null=True)),
                ('crystals', models.IntegerField(blank=True, default=None, null=True)),
                ('crystals_paid', models.IntegerField(blank=True, default=None, null=True)),
                ('last_login', models.DateTimeField(blank=True, default=None, null=True)),
                ('country', models.CharField(blank=True, default=None, max_length=5, null=True)),
                ('lang', models.CharField(blank=True, default=None, max_length=5, null=True)),
                ('level', models.SmallIntegerField(blank=True, default=None, null=True)),
                ('energy', models.IntegerField(blank=True, default=None, null=True)),
                ('energy_max', models.SmallIntegerField(blank=True, default=None, null=True)),
                ('arena_wing', models.IntegerField(blank=True, default=None, null=True)),
                ('glory_point', models.IntegerField(blank=True, default=None, null=True)),
                ('guild_point', models.IntegerField(blank=True, default=None, null=True)),
                ('rta_point', models.IntegerField(blank=True, default=None, null=True)),
                ('rta_mark', models.IntegerField(blank=True, default=None, null=True)),
                ('event_coin', models.IntegerField(blank=True, default=None, null=True)),
                ('antibot_count', models.IntegerField(blank=True, default=None, null=True)),
                ('raid_level', models.SmallIntegerField(blank=True, default=None, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('storage_capacity', models.SmallIntegerField(blank=True, default=None, null=True)),
                ('last_update', models.DateTimeField()),
                ('guild', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='website.Guild')),
            ],
        ),
        migrations.CreateModel(
            name='WizardItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField()),
                ('master_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='website.Item')),
                ('wizard', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='website.Wizard')),
            ],
            options={
                'ordering': ['wizard', 'master_item', '-quantity'],
            },
        ),
        migrations.CreateModel(
            name='WizardHomunculus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('build', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='website.HomunculusBuild')),
                ('homunculus', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='website.Monster')),
                ('wizard', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='website.Wizard')),
            ],
            options={
                'ordering': ['wizard', 'homunculus'],
            },
        ),
        migrations.CreateModel(
            name='WizardBuilding',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('level', models.SmallIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(10)])),
                ('building', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='website.Building')),
                ('wizard', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='website.Wizard')),
            ],
            options={
                'ordering': ['wizard', '-level', 'building'],
            },
        ),
        migrations.CreateModel(
            name='SiegeRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('win', models.IntegerField()),
                ('lose', models.IntegerField()),
                ('ratio', models.FloatField()),
                ('last_update', models.DateTimeField()),
                ('leader', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='siege_defense_leader', to='website.Monster')),
                ('monsters', models.ManyToManyField(related_name='siege_defense_monsters', to='website.Monster')),
                ('wizard', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='website.Wizard')),
            ],
            options={
                'ordering': ['-win', '-ratio'],
            },
        ),
        migrations.CreateModel(
            name='RuneRTA',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('monster', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='website.Monster')),
                ('rune', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='website.Rune')),
            ],
            options={
                'verbose_name': 'Rune RTA',
                'verbose_name_plural': 'Runes RTA',
                'ordering': ['monster', 'rune'],
            },
        ),
        migrations.AddField(
            model_name='rune',
            name='rune_set',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='website.RuneSet'),
        ),
        migrations.AddField(
            model_name='rune',
            name='wizard',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='website.Wizard'),
        ),
        migrations.CreateModel(
            name='RiftDungeonRun',
            fields=[
                ('battle_key', models.BigIntegerField(primary_key=True, serialize=False, unique=True)),
                ('dungeon', models.IntegerField(choices=[(1001, 'Ice Beast'), (2001, 'Fire Beast'), (3001, 'Wind Beast'), (4001, 'Light Beast'), (5001, 'Dark Beast')])),
                ('win', models.BooleanField(blank=True, null=True)),
                ('clear_time', models.DurationField(blank=True, null=True)),
                ('clear_rating', models.IntegerField(blank=True, choices=[(1, 'F'), (2, 'D'), (3, 'C'), (4, 'B-'), (5, 'B'), (6, 'B+'), (7, 'A-'), (8, 'A'), (9, 'A+'), (10, 'S'), (11, 'SS'), (12, 'SSS')], null=True)),
                ('dmg_phase_1', models.IntegerField(default=0)),
                ('dmg_phase_glory', models.IntegerField(default=0)),
                ('dmg_phase_2', models.IntegerField(default=0)),
                ('dmg_total', models.IntegerField()),
                ('date', models.DateTimeField(blank=True, null=True)),
                ('monsters', models.ManyToManyField(to='website.Monster')),
                ('wizard', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='website.Wizard')),
            ],
            options={
                'ordering': ['dungeon', '-clear_rating', '-dmg_total'],
            },
        ),
        migrations.CreateModel(
            name='MonsterRep',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('monster', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='website.Monster')),
                ('wizard', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='website.Wizard')),
            ],
        ),
        migrations.CreateModel(
            name='MonsterHoh',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_open', models.DateField()),
                ('date_close', models.DateField()),
                ('monster', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='website.MonsterBase')),
            ],
            options={
                'ordering': ['date_open', 'monster'],
            },
        ),
        migrations.CreateModel(
            name='MonsterFusion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cost', models.IntegerField()),
                ('monster', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='website.MonsterBase')),
            ],
            options={
                'ordering': ['monster'],
            },
        ),
        migrations.AddField(
            model_name='monsterbase',
            name='family',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='website.MonsterFamily'),
        ),
        migrations.AddField(
            model_name='monster',
            name='base_monster',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='website.MonsterBase'),
        ),
        migrations.AddField(
            model_name='monster',
            name='runes',
            field=models.ManyToManyField(blank=True, related_name='equipped_runes', related_query_name='equipped_runes', to='website.Rune'),
        ),
        migrations.AddField(
            model_name='monster',
            name='source',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='website.MonsterSource'),
        ),
        migrations.AddField(
            model_name='monster',
            name='wizard',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='website.Wizard'),
        ),
        migrations.AddField(
            model_name='homunculusbuild',
            name='depth_1',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='depth_1', to='website.HomunculusSkill'),
        ),
        migrations.AddField(
            model_name='homunculusbuild',
            name='depth_2',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='depth_2', to='website.HomunculusSkill'),
        ),
        migrations.AddField(
            model_name='homunculusbuild',
            name='depth_3',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='depth_3', to='website.HomunculusSkill'),
        ),
        migrations.AddField(
            model_name='homunculusbuild',
            name='depth_4',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='depth_4', to='website.HomunculusSkill'),
        ),
        migrations.AddField(
            model_name='homunculusbuild',
            name='depth_5',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='depth_5', to='website.HomunculusSkill'),
        ),
        migrations.AddField(
            model_name='homunculusbuild',
            name='homunculus',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='website.MonsterBase'),
        ),
        migrations.CreateModel(
            name='DungeonRun',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False, unique=True)),
                ('dungeon', models.IntegerField(choices=[(1001, 'Hall of Dark'), (2001, 'Hall of Fire'), (3001, 'Hall of Water'), (4001, 'Hall of Wind'), (5001, 'Hall of Magic'), (6001, 'Necropolis'), (7001, 'Hall of Light'), (8001, 'Giants Keep'), (9001, 'Dragons Lair'), (999999999, 'Rift of Worlds')])),
                ('stage', models.IntegerField()),
                ('win', models.BooleanField()),
                ('clear_time', models.DurationField(blank=True, null=True)),
                ('date', models.DateTimeField()),
                ('monsters', models.ManyToManyField(to='website.Monster')),
                ('wizard', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='website.Wizard')),
            ],
            options={
                'ordering': ['dungeon', '-stage', '-clear_time', '-win'],
            },
        ),
        migrations.CreateModel(
            name='DimensionHoleRun',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dungeon', models.IntegerField(choices=[(1101, 'Ellunia'), (1201, 'Fairy (Ellunia)'), (1202, 'Pixie (Ellunia)'), (2101, 'Karzhan'), (2202, 'Inugami (Karzhan)'), (2201, 'Warbear (Karzhan)'), (3101, 'Lumel'), (3201, 'Werewolf (Lumel)'), (3203, 'Martial Cat (Lumel)')])),
                ('stage', models.IntegerField()),
                ('win', models.BooleanField()),
                ('practice', models.BooleanField()),
                ('clear_time', models.DurationField(blank=True, null=True)),
                ('date', models.DateTimeField()),
                ('monsters', models.ManyToManyField(to='website.Monster')),
                ('wizard', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='website.Wizard')),
            ],
            options={
                'ordering': ['dungeon', '-stage', 'clear_time', 'win'],
            },
        ),
        migrations.CreateModel(
            name='Deck',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False, unique=True)),
                ('place', models.IntegerField(choices=[(1, 'Arena'), (2, 'Guild War'), (3, 'Raid'), (4, 'Lab Normal'), (5, 'Lab Rescue'), (6, 'ToA'), (7, 'Lab Speed Limit'), (8, 'Lab Time Limit'), (9, 'Lab Cooldown'), (10, 'Lab Explode'), (11, 'Lab Boss')])),
                ('number', models.SmallIntegerField()),
                ('team_runes_eff', models.FloatField(validators=[django.core.validators.MinValueValidator(0.0)])),
                ('leader', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='website.Monster')),
                ('monsters', models.ManyToManyField(related_name='monsters_in_deck', related_query_name='monsters_in_deck', to='website.Monster')),
                ('wizard', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='website.Wizard')),
            ],
            options={
                'ordering': ['-team_runes_eff', 'place', 'number'],
            },
        ),
        migrations.CreateModel(
            name='Arena',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('wins', models.IntegerField()),
                ('loses', models.IntegerField()),
                ('rank', models.IntegerField(choices=[(901, 'Beginner'), (1001, 'Challenger I'), (1002, 'Challenger II'), (1003, 'Challenger III'), (2001, 'Fighter I'), (2002, 'Fighter II'), (2003, 'Fighter III'), (3001, 'Conqueror I'), (3002, 'Conqueror II'), (3003, 'Conqueror III'), (4001, 'Guardian I'), (4002, 'Guardian II'), (4003, 'Guardian III'), (5001, 'Legend')])),
                ('def_1', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='first_def_monster', to='website.Monster')),
                ('def_2', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='second_def_monster', to='website.Monster')),
                ('def_3', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='third_def_monster', to='website.Monster')),
                ('def_4', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='fourth_def_monster', to='website.Monster')),
                ('wizard', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='website.Wizard')),
            ],
            options={
                'ordering': ['-rank', '-wins', 'loses'],
            },
        ),
    ]