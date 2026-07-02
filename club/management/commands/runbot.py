import asyncio

from aiogram import Bot
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from club.services import get_or_create_telegram_user, today_stats


PROFILE_BUTTON = "Profil"
RULES_BUTTON = "Qoidalar"
ADMIN_BUTTON = "Admin"


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    allowed = []
    for char in text.casefold():
        if char.isalnum() or char.isspace():
            allowed.append(char)
    return " ".join("".join(allowed).split())


def is_menu_text(message: Message, *labels: str) -> bool:
    text = clean_text(message.text)
    return any(
        text == clean_text(label) or text.endswith(f" {clean_text(label)}")
        for label in labels
    )


def is_admin_user(message: Message) -> bool:
    return bool(settings.ADMIN_IDS and message.from_user and message.from_user.id in settings.ADMIN_IDS)


def main_keyboard(is_admin: bool = False):
    keyboard = [
        [KeyboardButton(text=f"👤 {PROFILE_BUTTON}"), KeyboardButton(text=f"ℹ️ {RULES_BUTTON}")],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text=f"🛠 {ADMIN_BUTTON}")])
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        input_field_placeholder="Bo'limni tanlang",
        is_persistent=True,
        resize_keyboard=True,
    )


def keyboard_for(message: Message):
    return main_keyboard(is_admin_user(message))


def admin_panel_url() -> str:
    return settings.MINI_APP_URL.rstrip("/").removesuffix("/app") + "/control/"


def admin_panel_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Admin panelni ochish", url=admin_panel_url())],
        ]
    )


async def send_profile(message: Message):
    user = await sync_to_async(get_or_create_telegram_user)(
        telegram_id=message.from_user.id,
        first_name=message.from_user.first_name or "",
        username=message.from_user.username or "",
    )
    rank = await sync_to_async(user.ranking_position)()
    await message.answer(
        f"👤 {user.full_name}\n"
        f"XP: {user.xp}\n"
        f"Streak: {user.streak}\n"
        f"League: {user.league_label}\n"
        f"Reyting: #{rank}",
        reply_markup=keyboard_for(message),
    )


async def send_report(message: Message):
    await message.answer(
        "Bugungi vazifalarni belgilab, hisobotni ilova orqali topshiring. Pastdagi ilova tugmasini bosing.",
        reply_markup=keyboard_for(message),
    )


async def send_rules(message: Message):
    await message.answer(
        "Qoidalar:\n"
        "1. Kuniga faqat 1 marta hisobot topshiriladi.\n"
        "2. Har vazifa 20 XP, kunlik maksimum 100 XP.\n"
        "3. Bir kun o'tkazib yuborilsa streak 0 dan boshlanadi, XP saqlanadi.\n"
        "4. Hisobotlar 1-versiyada ishonch asosida qabul qilinadi.",
        reply_markup=keyboard_for(message),
    )


async def send_admin(message: Message):
    if not is_admin_user(message):
        return
    data = await sync_to_async(today_stats)()
    await message.answer(
        "🛠 Admin bo'limi\n\n"
        f"Bugungi hisobotlar: {data['reports_today']}\n"
        f"Bugungi XP: {data['xp_today']}\n"
        f"Jami foydalanuvchi: {data['users_total']}\n\n"
        "Batafsil boshqarish uchun admin panelga kiring.",
        reply_markup=admin_panel_keyboard(),
    )


def command_name(text: str) -> str:
    command = text.split(maxsplit=1)[0]
    return command.split("@", 1)[0].casefold()


async def handle_message(message: Message):
    text = message.text or ""
    command = command_name(text) if text.startswith("/") else ""

    if command == "/start":
        referral_code = ""
        if len(text.split(maxsplit=1)) == 2:
            referral_code = text.split(maxsplit=1)[1].strip()
        user = await sync_to_async(get_or_create_telegram_user)(
            telegram_id=message.from_user.id,
            first_name=message.from_user.first_name or "",
            username=message.from_user.username or "",
            referral_code=referral_code,
        )
        await message.answer(
            "ZIYO | INTIZOM CLUB\n\n"
            f"Salom, {user.full_name}.\n\n"
            "Intizom motivatsiyadan kuchli. Kunlik hisobot topshiring, XP yig'ing va reytingda o'sing.\n\n"
            "Pastdagi tugmalar orqali profilingizni ko'ring yoki qoidalarni o'qing."
            + ("\n\nAdmin uchun boshqaruv tugmasi ham qo'shildi." if is_admin_user(message) else ""),
            reply_markup=keyboard_for(message),
        )
        return

    if command == "/profile" or is_menu_text(message, PROFILE_BUTTON):
        await send_profile(message)
        return

    if command == "/rules" or is_menu_text(message, RULES_BUTTON):
        await send_rules(message)
        return

    if command == "/admin" or is_menu_text(message, ADMIN_BUTTON):
        await send_admin(message)
        return

    if command == "/report":
        await send_report(message)
        return

    if command == "/stats":
        if settings.ADMIN_IDS and message.from_user.id not in settings.ADMIN_IDS:
            return
        data = await sync_to_async(today_stats)()
        await message.answer(
            f"Bugungi statistika:\n"
            f"Jami foydalanuvchi: {data['users_total']}\n"
            f"Bugun hisobot: {data['reports_today']}\n"
            f"Bugun XP: {data['xp_today']}",
            reply_markup=keyboard_for(message),
        )
        return

    await message.answer(
        "Pastdagi tugmalardan birini tanlang.",
        reply_markup=keyboard_for(message),
    )


class Command(BaseCommand):
    help = "Telegram botni polling rejimida ishga tushiradi"

    def handle(self, *args, **options):
        if not settings.BOT_TOKEN:
            raise CommandError("BOT_TOKEN .env faylda berilmagan.")

        async def runner():
            bot = Bot(settings.BOT_TOKEN)
            offset = None
            await bot.delete_webhook(drop_pending_updates=True)
            try:
                while True:
                    updates = await bot.get_updates(offset=offset, timeout=30, allowed_updates=["message"])
                    for update in updates:
                        offset = update.update_id + 1
                        if update.message:
                            await handle_message(update.message)
            finally:
                await bot.session.close()

        asyncio.run(runner())
