import asyncio

from aiogram import Bot
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from club.models import DailyReport, UserProfile


class Command(BaseCommand):
    help = "Telegram foydalanuvchilariga ertalabki yoki kechki eslatma yuboradi"

    def add_arguments(self, parser):
        parser.add_argument(
            "kind",
            choices=["morning", "evening"],
            help="morning: 06:00 motivatsiya, evening: 21:00 hisobot eslatmasi",
        )

    def handle(self, *args, **options):
        if not settings.BOT_TOKEN:
            raise CommandError("BOT_TOKEN .env faylda berilmagan.")

        kind = options["kind"]
        today = timezone.localdate()
        if kind == "morning":
            users = UserProfile.objects.filter(is_blocked=False)
            text = "Hayrli tong! Bugun intizom uchun yana bir imkoniyat. ZIYO | INTIZOM CLUB"
        else:
            reported_ids = DailyReport.objects.filter(date=today).values_list("user_id", flat=True)
            users = UserProfile.objects.filter(is_blocked=False).exclude(id__in=reported_ids)
            text = "Bugungi hisobotni topshirishni unutmang. Intizom motivatsiyadan kuchli."

        async def runner():
            bot = Bot(settings.BOT_TOKEN)
            sent = 0
            for user in users.iterator():
                try:
                    await bot.send_message(user.telegram_id, text)
                    sent += 1
                except Exception as exc:
                    self.stderr.write(f"{user.telegram_id}: {exc}")
            await bot.session.close()
            self.stdout.write(self.style.SUCCESS(f"{sent} ta xabar yuborildi."))

        asyncio.run(runner())
