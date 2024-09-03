import asyncio
from django.core.management.base import BaseCommand
from shop.tasks import main

class Command(BaseCommand):
    help = 'Scrape car data and save it to the database'

    def handle(self, *args, **kwargs):
        asyncio.run(main())
        self.stdout.write(self.style.SUCCESS('Successfully scraped car data'))