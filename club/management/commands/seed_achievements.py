from django.core.management.base import BaseCommand

from club.models import Achievement


class Command(BaseCommand):
    help = "Default achievement badge'larini yaratadi"

    def handle(self, *args, **options):
        Achievement.seed_defaults()
        self.stdout.write(self.style.SUCCESS("Achievement badge'lari tayyor."))
