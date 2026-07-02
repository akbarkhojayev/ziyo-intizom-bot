# Generated for ZIYO Intizom Club MVP.

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Achievement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=120)),
                ("description", models.CharField(max_length=255)),
                (
                    "criteria",
                    models.CharField(
                        choices=[
                            ("streak_days", "Streak kunlari"),
                            ("book_reports", "Kitob hisobotlari"),
                            ("sport_reports", "Sport hisobotlari"),
                            ("prayer_reports", "Namoz hisobotlari"),
                            ("referrals", "Do'st takliflari"),
                            ("league_legend", "Legend league"),
                        ],
                        max_length=32,
                    ),
                ),
                ("threshold", models.PositiveIntegerField(default=1)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["threshold", "name"]},
        ),
        migrations.CreateModel(
            name="Announcement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=120)),
                ("text", models.TextField()),
                ("is_sent", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("telegram_id", models.BigIntegerField(unique=True)),
                ("username", models.CharField(blank=True, max_length=64)),
                ("first_name", models.CharField(blank=True, max_length=128)),
                ("full_name", models.CharField(max_length=160)),
                ("age", models.PositiveSmallIntegerField(blank=True, null=True)),
                (
                    "gender",
                    models.CharField(
                        choices=[("male", "Erkak"), ("female", "Ayol"), ("other", "Aytilmagan")],
                        default="other",
                        max_length=16,
                    ),
                ),
                ("region", models.CharField(blank=True, max_length=120)),
                (
                    "main_goal",
                    models.CharField(
                        choices=[
                            ("discipline", "Intizom"),
                            ("wake_early", "Erta turish"),
                            ("sport", "Sport"),
                            ("weight_loss", "Vazn tashlash"),
                            ("quit_smoking", "Sigaret tashlash"),
                            ("book", "Kitob"),
                            ("saving", "Pul yig'ish"),
                            ("prayer", "Namoz"),
                            ("other", "Boshqa"),
                        ],
                        default="discipline",
                        max_length=32,
                    ),
                ),
                ("xp", models.PositiveIntegerField(default=0)),
                ("streak", models.PositiveIntegerField(default=0)),
                ("last_report_date", models.DateField(blank=True, null=True)),
                ("referral_code", models.CharField(blank=True, max_length=16, unique=True)),
                ("is_blocked", models.BooleanField(default=False)),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "referred_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="referrals",
                        to="club.userprofile",
                    ),
                ),
            ],
            options={"ordering": ["-xp", "joined_at"]},
        ),
        migrations.CreateModel(
            name="DailyReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(default=django.utils.timezone.localdate)),
                ("wake_early", models.BooleanField(default=False)),
                ("prayer", models.BooleanField(default=False)),
                ("sport", models.BooleanField(default=False)),
                ("book", models.BooleanField(default=False)),
                ("goal_written", models.BooleanField(default=False)),
                ("xp_earned", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reports", to="club.userprofile"),
                ),
            ],
            options={"ordering": ["-date", "-created_at"]},
        ),
        migrations.CreateModel(
            name="UserAchievement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("unlocked_at", models.DateTimeField(auto_now_add=True)),
                (
                    "achievement",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="club.achievement"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="achievements", to="club.userprofile"),
                ),
            ],
            options={"ordering": ["-unlocked_at"]},
        ),
        migrations.CreateModel(
            name="XPTransaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.IntegerField()),
                (
                    "reason",
                    models.CharField(
                        choices=[
                            ("daily_report", "Kunlik hisobot"),
                            ("admin_adjustment", "Admin o'zgartirish"),
                            ("referral", "Referral"),
                        ],
                        max_length=32,
                    ),
                ),
                ("note", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "report",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="club.dailyreport"),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="xp_transactions",
                        to="club.userprofile",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="dailyreport",
            constraint=models.UniqueConstraint(fields=("user", "date"), name="unique_daily_report_per_user"),
        ),
        migrations.AddConstraint(
            model_name="userachievement",
            constraint=models.UniqueConstraint(fields=("user", "achievement"), name="unique_user_achievement"),
        ),
    ]
