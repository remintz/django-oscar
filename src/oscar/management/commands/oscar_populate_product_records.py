import logging
import json
import random

from django.core.management.base import BaseCommand
from oscar.core.loading import get_class

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate and persist products records (stats)'

    def handle(self, *args, **options):
        list = []
        pk = 1

        for i in range(12,210):
            num_views = random.randrange(100000)
            num_basket_additions = random.randrange(num_views-1)
            num_purchases = random.randrange(num_basket_additions-1)

            list.append({
            "pk": pk,
            "model": "analytics.ProductRecord",
            "fields": {
                "num_views": num_views,
                "num_basket_additions": num_basket_additions,
                "num_purchases": num_purchases,
                "score": 0,
                "product": i
                }
            })
            pk += 1

        with open("sandbox/fixtures/product-records.json","w") as f:
            json.dump(list,f)
        f.close()
        