# ZIYO | Intizom Club

Telegram bot ichida ishlaydigan intizom MVP: Django admin/backend, Telegram Mini App, XP, streak, league, reyting, achievement va referral.

## Ishga tushirish

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_achievements
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```

Mini App lokal manzili:

```text
http://127.0.0.1:8000/app/
```

Admin panel:

```text
http://127.0.0.1:8000/admin/
```

## Telegram bot

`.env` ichida `BOT_TOKEN`, `MINI_APP_URL` va kerak bo'lsa `ADMIN_IDS` ni to'ldiring.

```bash
.venv/bin/python manage.py runbot
```

Bot komandalar:

- `/start` - foydalanuvchini yaratadi va Mini App tugmasini beradi
- `/profile` - profil va XP
- `/report` - Mini App orqali hisobot
- `/rules` - qoidalar
- `/stats` - admin statistikasi

## Reminder

Cron yoki systemd timer orqali:

```bash
.venv/bin/python manage.py send_reminders morning
.venv/bin/python manage.py send_reminders evening
```

Production server uchun systemd timer fayllari `deploy/systemd/` ichida:

- `ziyo-reminder-morning.timer` - har kuni `06:00 Asia/Tashkent`
- `ziyo-reminder-evening.timer` - har kuni `21:00 Asia/Tashkent`

TZ bo'yicha tavsiya qilingan vaqtlar:

- `06:00` - motivatsiya
- `21:00` - hisobot eslatmasi

## MVP ichida bor

- Registratsiya
- Kunlik hisobot, kuniga 1 marta
- Har vazifa 20 XP, kunlik maksimum 100 XP
- XP, streak, league
- Umumiy, haftalik, oylik reyting
- Achievement badge'lari
- Referral code/link
- Django admin panel
- Telegram bot polling komandasi
- Morning/evening reminder komandasi

## Tekshiruv

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py test
```
