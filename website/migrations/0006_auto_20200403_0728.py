# Generated by Django 3.0.4 on 2020-04-03 07:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0005_auto_20200319_1703'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dimensionholerun',
            name='dungeon',
            field=models.IntegerField(choices=[(1101, 'Ellunia'), (1201, 'Fairy (Ellunia)'), (1202, 'Pixie (Ellunia)'), (2101, 'Karzhan'), (2201, 'Warbear (Karzhan)'), (2202, 'Inugami (Karzhan)'), (2203, 'Griffon (Karzhan)'), (3101, 'Lumel'), (3201, 'Werewolf (Lumel)'), (3202, 'Martial Cat (Lumel)')], db_index=True),
        ),
    ]