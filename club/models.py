from __future__ import annotations

import secrets
from datetime import timedelta

from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone


class Goal(models.TextChoices):
    DISCIPLINE = "discipline", "Intizom"
    WAKE_EARLY = "wake_early", "Erta turish"
    SPORT = "sport", "Sport"
    WEIGHT_LOSS = "weight_loss", "Vazn tashlash"
    QUIT_SMOKING = "quit_smoking", "Sigaret tashlash"
    BOOK = "book", "Kitob"
    SAVING = "saving", "Pul yig'ish"
    PRAYER = "prayer", "Namoz"
    OTHER = "other", "Boshqa"


class Gender(models.TextChoices):
    MALE = "male", "Erkak"
    FEMALE = "female", "Ayol"
    OTHER = "other", "Aytilmagan"


class League(models.TextChoices):
    BRONZE = "bronze", "Bronze"
    SILVER = "silver", "Silver"
    GOLD = "gold", "Gold"
    DIAMOND = "diamond", "Diamond"
    LEGEND = "legend", "Legend"


class TaskCode(models.TextChoices):
    WAKE_EARLY = "wake_early", "Erta turdim"
    PRAYER = "prayer", "Namoz"
    SPORT = "sport", "Sport"
    BOOK = "book", "Kitob"
    GOAL_WRITTEN = "goal_written", "Maqsad yozdim"


TASK_XP = 20


class UserProfile(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=64, blank=True)
    first_name = models.CharField(max_length=128, blank=True)
    full_name = models.CharField(max_length=160)
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=16, choices=Gender.choices, default=Gender.OTHER)
    region = models.CharField(max_length=120, blank=True)
    main_goal = models.CharField(max_length=32, choices=Goal.choices, default=Goal.DISCIPLINE)
    xp = models.PositiveIntegerField(default=0)
    streak = models.PositiveIntegerField(default=0)
    last_report_date = models.DateField(null=True, blank=True)
    referral_code = models.CharField(max_length=16, unique=True, blank=True)
    referred_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="referrals",
    )
    is_blocked = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-xp", "joined_at"]

    def __str__(self):
        return f"{self.full_name} ({self.telegram_id})"

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = self.generate_referral_code()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_referral_code() -> str:
        while True:
            code = secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:10]
            if not UserProfile.objects.filter(referral_code=code).exists():
                return code

    @property
    def league(self) -> str:
        if self.xp >= 18000:
            return League.LEGEND
        if self.xp >= 12001:
            return League.DIAMOND
        if self.xp >= 7001:
            return League.GOLD
        if self.xp >= 3001:
            return League.SILVER
        return League.BRONZE

    @property
    def league_label(self) -> str:
        return League(self.league).label

    def ranking_position(self, since=None) -> int:
        qs = UserProfile.objects.filter(is_blocked=False)
        if since:
            totals = (
                XPTransaction.objects.filter(created_at__date__gte=since)
                .values("user_id")
                .annotate(total=Sum("amount"))
                .order_by("-total", "user_id")
            )
            ids = [row["user_id"] for row in totals if row["total"] > 0]
            return ids.index(self.id) + 1 if self.id in ids else len(ids) + 1
        return qs.filter(xp__gt=self.xp).count() + 1


class DailyReport(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="reports")
    date = models.DateField(default=timezone.localdate)
    wake_early = models.BooleanField(default=False)
    prayer = models.BooleanField(default=False)
    sport = models.BooleanField(default=False)
    book = models.BooleanField(default=False)
    goal_written = models.BooleanField(default=False)
    xp_earned = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "date"], name="unique_daily_report_per_user")
        ]
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.user.full_name} - {self.date} (+{self.xp_earned})"

    @classmethod
    def submit(cls, user: UserProfile, tasks: list[str], report_date=None) -> "DailyReport":
        report_date = report_date or timezone.localdate()
        valid_tasks = {choice.value for choice in TaskCode}
        selected = sorted(set(tasks) & valid_tasks)
        xp = min(len(selected) * TASK_XP, 100)

        with transaction.atomic():
            user = UserProfile.objects.select_for_update().get(pk=user.pk)
            report, created = cls.objects.get_or_create(
                user=user,
                date=report_date,
                defaults={
                    "wake_early": TaskCode.WAKE_EARLY in selected,
                    "prayer": TaskCode.PRAYER in selected,
                    "sport": TaskCode.SPORT in selected,
                    "book": TaskCode.BOOK in selected,
                    "goal_written": TaskCode.GOAL_WRITTEN in selected,
                    "xp_earned": xp,
                },
            )
            if not created:
                return report

            yesterday = report_date - timedelta(days=1)
            user.streak = user.streak + 1 if user.last_report_date == yesterday else 1
            user.last_report_date = report_date
            user.xp += xp
            user.save(update_fields=["streak", "last_report_date", "xp", "updated_at"])

            XPTransaction.objects.create(
                user=user,
                amount=xp,
                reason=XPTransaction.Reason.DAILY_REPORT,
                report=report,
            )
            Achievement.check_for(user)
            ReferralReward.check_for(user.referred_by) if user.referred_by_id else None
            return report


class XPTransaction(models.Model):
    class Reason(models.TextChoices):
        DAILY_REPORT = "daily_report", "Kunlik hisobot"
        ADMIN_ADJUSTMENT = "admin_adjustment", "Admin o'zgartirish"
        REFERRAL = "referral", "Referral"

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="xp_transactions")
    amount = models.IntegerField()
    reason = models.CharField(max_length=32, choices=Reason.choices)
    note = models.CharField(max_length=255, blank=True)
    report = models.ForeignKey(DailyReport, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.full_name}: {self.amount} XP"


class RunSession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="run_sessions")
    date = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    last_latitude = models.FloatField(null=True, blank=True)
    last_longitude = models.FloatField(null=True, blank=True)
    last_recorded_at = models.DateTimeField(null=True, blank=True)
    distance_m = models.PositiveIntegerField(default=0)
    duration_s = models.PositiveIntegerField(default=0)
    avg_speed_kmh = models.FloatField(default=0)
    samples_count = models.PositiveIntegerField(default=0)
    rejection_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.user.full_name} - {self.date} ({self.status})"

    @property
    def is_verified(self) -> bool:
        return self.status == self.Status.VERIFIED


class Achievement(models.Model):
    class Criteria(models.TextChoices):
        STREAK_DAYS = "streak_days", "Streak kunlari"
        BOOK_REPORTS = "book_reports", "Kitob hisobotlari"
        SPORT_REPORTS = "sport_reports", "Sport hisobotlari"
        PRAYER_REPORTS = "prayer_reports", "Namoz hisobotlari"
        REFERRALS = "referrals", "Do'st takliflari"
        LEAGUE_LEGEND = "league_legend", "Legend league"

    code = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=255)
    criteria = models.CharField(max_length=32, choices=Criteria.choices)
    threshold = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["threshold", "name"]

    def __str__(self):
        return self.name

    @classmethod
    def seed_defaults(cls):
        defaults = [
            ("streak-7", "7 kun intizom", "7 kun ketma-ket hisobot", cls.Criteria.STREAK_DAYS, 7),
            ("book-30", "30 kun kitob", "30 marta kitob vazifasi", cls.Criteria.BOOK_REPORTS, 30),
            ("sport-100", "100 sport", "100 marta sport vazifasi", cls.Criteria.SPORT_REPORTS, 100),
            ("prayer-100", "100 namoz", "100 marta namoz vazifasi", cls.Criteria.PRAYER_REPORTS, 100),
            ("legend-180", "Legend", "180 kunlik kuchli intizom", cls.Criteria.STREAK_DAYS, 180),
            ("ref-3", "3 do'st", "3 ta do'st taklif qilish", cls.Criteria.REFERRALS, 3),
            ("ref-10", "10 do'st", "10 ta do'st taklif qilish", cls.Criteria.REFERRALS, 10),
            ("ref-20", "20 do'st", "20 ta do'st taklif qilish", cls.Criteria.REFERRALS, 20),
            ("ref-50", "50 do'st", "50 ta do'st taklif qilish", cls.Criteria.REFERRALS, 50),
        ]
        for code, name, description, criteria, threshold in defaults:
            cls.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": description,
                    "criteria": criteria,
                    "threshold": threshold,
                },
            )

    @classmethod
    def check_for(cls, user: UserProfile):
        cls.seed_defaults()
        for achievement in cls.objects.filter(is_active=True):
            if achievement.is_unlocked_by(user):
                UserAchievement.objects.get_or_create(user=user, achievement=achievement)

    def is_unlocked_by(self, user: UserProfile) -> bool:
        if self.criteria == self.Criteria.STREAK_DAYS:
            return user.streak >= self.threshold
        if self.criteria == self.Criteria.BOOK_REPORTS:
            return user.reports.filter(book=True).count() >= self.threshold
        if self.criteria == self.Criteria.SPORT_REPORTS:
            return user.reports.filter(sport=True).count() >= self.threshold
        if self.criteria == self.Criteria.PRAYER_REPORTS:
            return user.reports.filter(prayer=True).count() >= self.threshold
        if self.criteria == self.Criteria.REFERRALS:
            return user.referrals.count() >= self.threshold
        if self.criteria == self.Criteria.LEAGUE_LEGEND:
            return user.league == League.LEGEND
        return False


class UserAchievement(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="achievements")
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "achievement"], name="unique_user_achievement")
        ]
        ordering = ["-unlocked_at"]

    def __str__(self):
        return f"{self.user.full_name} - {self.achievement.name}"


class ReferralReward:
    @staticmethod
    def check_for(user: UserProfile | None):
        if user:
            Achievement.check_for(user)


class Announcement(models.Model):
    title = models.CharField(max_length=120)
    text = models.TextField()
    is_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
