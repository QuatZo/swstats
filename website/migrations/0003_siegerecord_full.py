# Generated by Django 3.0.3 on 2020-03-17 13:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0002_auto_20200304_2011'),
    ]

    operations = [
        migrations.AddField(
            model_name='siegerecord',
            name='full',
            field=models.BooleanField(default=True),
        ),
    ]
