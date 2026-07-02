from datetime import date, timedelta

from django.db.models import Sum
from django.utils import timezone

from .models import Achievement, DailyReport, TaskCode, UserProfile, XPTransaction


def get_or_create_telegram_user(
    telegram_id: int,
    first_name: str = "",
    username: str = "",
    referral_code: str = "",
) -> UserProfile:
    referrer = None
    if referral_code:
        referrer = UserProfile.objects.filter(referral_code=referral_code).first()

    user, created = UserProfile.objects.get_or_create(
        telegram_id=telegram_id,
        defaults={
            "full_name": first_name or f"User {telegram_id}",
            "first_name": first_name,
            "username": username,
            "referred_by": referrer,
        },
    )
    updates = []
    if first_name and user.first_name != first_name:
        user.first_name = first_name
        updates.append("first_name")
    if username and user.username != username:
        user.username = username
        updates.append("username")
    if updates:
        updates.append("updated_at")
        user.save(update_fields=updates)

    if created and referrer:
        Achievement.check_for(referrer)
    return user


def leaderboard(period: str = "all", user: UserProfile | None = None, limit: int = 20):
    if period == "week":
        since = timezone.localdate() - timedelta(days=7)
    elif period == "month":
        since = timezone.localdate().replace(day=1)
    elif period == "year":
        today = timezone.localdate()
        since = date(today.year, 1, 1)
    else:
        since = None

    if since:
        rows = (
            XPTransaction.objects.filter(created_at__date__gte=since, user__is_blocked=False)
            .values("user_id", "user__full_name", "user__xp", "user__streak")
            .annotate(score=Sum("amount"))
            .filter(score__gt=0)
            .order_by("-score", "user__joined_at")[:limit]
        )
        return [
            {
                "rank": index + 1,
                "name": row["user__full_name"],
                "xp": row["score"],
                "total_xp": row["user__xp"],
                "streak": row["user__streak"],
                "is_me": user and row["user_id"] == user.id,
            }
            for index, row in enumerate(rows)
        ]

    users = UserProfile.objects.filter(is_blocked=False).order_by("-xp", "joined_at")[:limit]
    return [
        {
            "rank": index + 1,
            "name": item.full_name,
            "xp": item.xp,
            "total_xp": item.xp,
            "streak": item.streak,
            "is_me": user and item.id == user.id,
        }
        for index, item in enumerate(users)
    ]


def today_stats():
    today = timezone.localdate()
    reports = DailyReport.objects.filter(date=today)
    return {
        "users_total": UserProfile.objects.count(),
        "reports_today": reports.count(),
        "xp_today": reports.aggregate(total=Sum("xp_earned"))["total"] or 0,
    }


def task_payload():
    return [{"code": choice.value, "label": choice.label, "xp": 20} for choice in TaskCode]
