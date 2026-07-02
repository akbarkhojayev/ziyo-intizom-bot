from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q, Sum
from django.shortcuts import render
from django.utils import timezone

from .models import Achievement, DailyReport, Gender, League, TaskCode, UserAchievement, UserProfile, XPTransaction


def percent(value, total):
    return round((value / total) * 100) if total else 0


@staff_member_required
def dashboard(request):
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    week_start = today - timedelta(days=6)
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    reports_today = DailyReport.objects.filter(date=today)
    reports_yesterday = DailyReport.objects.filter(date=yesterday)
    reports_week = DailyReport.objects.filter(date__gte=week_start)
    reports_month = DailyReport.objects.filter(date__gte=month_start)
    reports_year = DailyReport.objects.filter(date__gte=year_start)
    users = UserProfile.objects.all()
    active_users = users.filter(is_blocked=False)
    user_total = users.count()
    active_total = active_users.count()
    today_report_count = reports_today.count()
    today_xp = reports_today.aggregate(total=Sum("xp_earned"))["total"] or 0
    total_xp = users.aggregate(total=Sum("xp"))["total"] or 0

    top_users = UserProfile.objects.filter(is_blocked=False).order_by("-xp", "joined_at")[:10]
    latest_reports = DailyReport.objects.select_related("user").order_by("-created_at")[:10]
    goal_rows = (
        UserProfile.objects.values("main_goal")
        .annotate(total=Count("id"))
        .order_by("-total")[:8]
    )

    goal_labels = dict(UserProfile._meta.get_field("main_goal").choices)
    gender_labels = dict(Gender.choices)
    task_map = [
        ("wake_early", TaskCode.WAKE_EARLY.label),
        ("prayer", TaskCode.PRAYER.label),
        ("sport", TaskCode.SPORT.label),
        ("book", TaskCode.BOOK.label),
        ("goal_written", TaskCode.GOAL_WRITTEN.label),
    ]
    task_counts = DailyReport.objects.aggregate(
        wake_early=Count("id", filter=Q(wake_early=True)),
        prayer=Count("id", filter=Q(prayer=True)),
        sport=Count("id", filter=Q(sport=True)),
        book=Count("id", filter=Q(book=True)),
        goal_written=Count("id", filter=Q(goal_written=True)),
    )
    max_task_count = max(task_counts.values()) if task_counts else 0

    league_counts = {choice.label: 0 for choice in League}
    for profile in active_users.only("xp"):
        league_counts[profile.league_label] += 1

    daily_rows = []
    max_daily_xp = 0
    for offset in range(13, -1, -1):
        day = today - timedelta(days=offset)
        day_reports = DailyReport.objects.filter(date=day)
        day_xp = day_reports.aggregate(total=Sum("xp_earned"))["total"] or 0
        max_daily_xp = max(max_daily_xp, day_xp)
        daily_rows.append(
            {
                "date": day.strftime("%d.%m"),
                "reports": day_reports.count(),
                "xp": day_xp,
            }
        )

    for row in daily_rows:
        row["percent"] = percent(row["xp"], max_daily_xp)

    region_rows = users.exclude(region="").values("region").annotate(total=Count("id")).order_by("-total")[:8]
    gender_rows = users.values("gender").annotate(total=Count("id")).order_by("-total")
    achievement_rows = (
        UserAchievement.objects.values("achievement__name")
        .annotate(total=Count("id"))
        .order_by("-total")[:8]
    )
    referral_rows = users.annotate(referral_total=Count("referrals")).filter(referral_total__gt=0).order_by("-referral_total")[:8]
    no_report_users = active_users.exclude(reports__date=today).count()

    context = {
        "title": "Statistika dashboard",
        "cards": [
            {"label": "Jami foydalanuvchi", "value": user_total, "tone": "primary"},
            {"label": "Aktiv foydalanuvchi", "value": active_total, "tone": "info"},
            {"label": "Bugungi hisobot", "value": today_report_count, "tone": "success"},
            {"label": "Bugungi XP", "value": today_xp, "tone": "warning"},
            {"label": "Bloklangan user", "value": UserProfile.objects.filter(is_blocked=True).count(), "tone": "danger"},
            {"label": "Jami XP", "value": total_xp, "tone": "warning"},
            {"label": "Jami hisobot", "value": DailyReport.objects.count(), "tone": "success"},
            {"label": "Achievement ochilgan", "value": UserAchievement.objects.count(), "tone": "info"},
        ],
        "quick_stats": [
            {"label": "Bugungi qatnashuv", "value": f"{percent(today_report_count, active_total)}%"},
            {"label": "Kecha hisobot", "value": reports_yesterday.count()},
            {"label": "Bugun hisobot topshirmagan", "value": no_report_users},
            {"label": "O'rtacha XP / hisobot", "value": round(today_xp / today_report_count) if today_report_count else 0},
        ],
        "periods": [
            {
                "label": "Bugun",
                "reports": reports_today.count(),
                "xp": today_xp,
            },
            {
                "label": "Kecha",
                "reports": reports_yesterday.count(),
                "xp": reports_yesterday.aggregate(total=Sum("xp_earned"))["total"] or 0,
            },
            {
                "label": "Haftalik",
                "reports": reports_week.count(),
                "xp": reports_week.aggregate(total=Sum("xp_earned"))["total"] or 0,
            },
            {
                "label": "Oylik",
                "reports": reports_month.count(),
                "xp": reports_month.aggregate(total=Sum("xp_earned"))["total"] or 0,
            },
            {
                "label": "Yillik",
                "reports": reports_year.count(),
                "xp": reports_year.aggregate(total=Sum("xp_earned"))["total"] or 0,
            },
            {
                "label": "Jami XP transaction",
                "reports": XPTransaction.objects.count(),
                "xp": XPTransaction.objects.aggregate(total=Sum("amount"))["total"] or 0,
            },
        ],
        "top_users": top_users,
        "latest_reports": latest_reports,
        "goal_rows": [
            {"label": goal_labels.get(row["main_goal"], row["main_goal"]), "total": row["total"], "percent": percent(row["total"], user_total)}
            for row in goal_rows
        ],
        "task_rows": [
            {"label": label, "total": task_counts[key], "percent": percent(task_counts[key], max_task_count)}
            for key, label in task_map
        ],
        "league_rows": [
            {"label": label, "total": total, "percent": percent(total, active_total)}
            for label, total in league_counts.items()
        ],
        "region_rows": [
            {"label": row["region"], "total": row["total"], "percent": percent(row["total"], user_total)}
            for row in region_rows
        ],
        "gender_rows": [
            {"label": gender_labels.get(row["gender"], row["gender"]), "total": row["total"], "percent": percent(row["total"], user_total)}
            for row in gender_rows
        ],
        "achievement_rows": [
            {"label": row["achievement__name"], "total": row["total"], "percent": percent(row["total"], active_total)}
            for row in achievement_rows
        ],
        "referral_rows": referral_rows,
        "daily_rows": daily_rows,
    }
    return render(request, "admin/club_dashboard.html", context)
