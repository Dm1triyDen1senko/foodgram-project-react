import csv

from django.core.management.base import BaseCommand

from recipes.models import Ingredient

PATH_CSV = 'data/ingredients.csv'


class Command(BaseCommand):
    help = 'Import data from CSV file into the database'

    def handle(self, *args, **kwargs):
        objects_to_create = []
        with open(PATH_CSV, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                objects_to_create.append(Ingredient(**row))
        Ingredient.objects.bulk_create(objects_to_create, batch_size=500)
        self.stdout.write(self.style.SUCCESS('Data imported successfully'))
