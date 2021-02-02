from django.core.management.base import BaseCommand

from website.views import bot_debug_get_all_monster_report

class Command(BaseCommand):
    help = 'Generates HTML Reports for all Base Monsters in Database'

    def handle(self, *args, **options):
        bot_debug_get_all_monster_report(None)
        self.stdout.write(self.style.SUCCESS('Done!'))
