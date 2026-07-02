import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from club.models import DailyReport
from club.services import get_or_create_telegram_user, today_stats


def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏠 Bosh sahifa"), KeyboardButton(text="✅ Bugungi hisobot")],
            [KeyboardButton(text="🏆 Reyting"), KeyboardButton(text="👤 Profil")],
            [KeyboardButton(text="ℹ️ Qoidalar")],
        ],
        resize_keyboard=True,
    )


def webapp_keyboard(text="ZIYO ilovasini ochish"):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=text,
                    web_app=WebAppInfo(url=settings.MINI_APP_URL),
                )
            ]
        ]
    )


async def register_handlers(dp: Dispatcher):
    @dp.message(CommandStart())
    async def start(message: Message):
        referral_code = ""
        if message.text and len(message.text.split(maxsplit=1)) == 2:
            referral_code = message.text.split(maxsplit=1)[1].strip()
        user = get_or_create_telegram_user(
            telegram_id=message.from_user.id,
            first_name=message.from_user.first_name or "",
            username=message.from_user.username or "",
            referral_code=referral_code,
        )
        await message.answer(
            "ZIYO | INTIZOM CLUB\n\n"
            "Intizom motivatsiyadan kuchli.\n"
            "Kunlik hisobot topshiring, XP yig'ing va reytingda o'sing.",
            reply_markup=main_keyboard(),
        )
        await message.answer(
            f"Salom, {user.full_name}. Ilovani ochib profilingizni to'ldiring.",
            reply_markup=webapp_keyboard(),
        )

    @dp.message(Command("profile"))
    @dp.message(F.text == "👤 Profil")
    async def profile(message: Message):
        user = get_or_create_telegram_user(
            telegram_id=message.from_user.id,
            first_name=message.from_user.first_name or "",
            username=message.from_user.username or "",
        )
        await message.answer(
            f"👤 {user.full_name}\n"
            f"XP: {user.xp}\n"
            f"Streak: {user.streak}\n"
            f"League: {user.league_label}\n"
            f"Reyting: #{user.ranking_position()}",
            reply_markup=webapp_keyboard("Profilni ochish"),
        )

    @dp.message(Command("report"))
    @dp.message(F.text.in_({"✅ Bugungi hisobot", "🏠 Bosh sahifa", "🏆 Reyting"}))
    async def open_app(message: Message):
        await message.answer("Hisobot va reyting Telegram ichidagi ilovada qulay ishlaydi.", reply_markup=webapp_keyboard())

    @dp.message(Command("rules"))
    @dp.message(F.text == "ℹ️ Qoidalar")
    async def rules(message: Message):
        await message.answer(
            "Qoidalar:\n"
            "1. Kuniga faqat 1 marta hisobot topshiriladi.\n"
            "2. Har vazifa 20 XP, kunlik maksimum 100 XP.\n"
            "3. Bir kun o'tkazib yuborilsa streak 0 dan boshlanadi, XP saqlanadi.\n"
            "4. Hisobotlar 1-versiyada ishonch asosida qabul qilinadi."
        )

    @dp.message(Command("stats"))
    async def stats(message: Message):
        if settings.ADMIN_IDS and message.from_user.id not in settings.ADMIN_IDS:
            return
        data = today_stats()
        await message.answer(
            f"Bugungi statistika:\n"
            f"Jami foydalanuvchi: {data['users_total']}\n"
            f"Bugun hisobot: {data['reports_today']}\n"
            f"Bugun XP: {data['xp_today']}"
        )


class Command(BaseCommand):
    help = "Telegram botni polling rejimida ishga tushiradi"

    def handle(self, *args, **options):
        if not settings.BOT_TOKEN:
            raise CommandError("BOT_TOKEN .env faylda berilmagan.")

        async def runner():
            bot = Bot(settings.BOT_TOKEN)
            dp = Dispatcher()
            await register_handlers(dp)
            await dp.start_polling(bot)

        asyncio.run(runner())
