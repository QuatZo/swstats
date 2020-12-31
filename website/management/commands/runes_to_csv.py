from django.core.management.base import BaseCommand
from website.models import Rune, RuneSet
from website.serializers import RuneSerializer

import os
import pandas as pd
import time


class Command(BaseCommand):
    help = 'Fetches all runes and saves them in CSV'

    def handle(self, *args, **options):
        start = time.time()
        qs = Rune.objects.all().select_related('rune_set')
        batch_size = 1000
        count = qs.count()
        pointer = 0
        csv_path = os.path.join(os.getcwd(), 'runes.csv')
        if os.path.exists(csv_path):
            os.remove(csv_path)
        self.stdout.write('Serializing data...')
        substats = ['sub_hp_flat', 'sub_hp', 'sub_atk_flat', 'sub_atk', 'sub_def_flat',
                    'sub_def', 'sub_speed', 'sub_crit_rate', 'sub_crit_dmg', 'sub_res', 'sub_acc']

        while pointer < count:
            self.stdout.write(
                f"{pointer}/{count} ({round(pointer / count * 100, 2)}%)")
            data = RuneSerializer(
                qs[pointer:min(pointer + batch_size, count)], many=True).data
            df = pd.DataFrame.from_records(data)
            for s in substats:
                df[s] = df[s].apply(lambda x: sum(
                    x) if isinstance(x, list) else None)
            df.to_csv(csv_path, mode='a+', index=False, line_terminator='')

            pointer += batch_size

        self.stdout.write(f'\t{round(time.time() - start, 4)} seconds')
        self.stdout.write(self.style.SUCCESS('Done!'))
