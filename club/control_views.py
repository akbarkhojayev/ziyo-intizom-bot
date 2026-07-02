from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Announcement, DailyReport, TaskCode, UserProfile, XPTransaction


def staff_required(view_func):
    return user_passes_test(lambda user: user.is_active and user.is_staff, login_url="club:control_login")(view_func)


def control_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("club:control_dashboard")

    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username", "").strip(),
            password=request.POST.get("password", ""),
        )
        if user and user.is_staff:
            login(request, user)
            return redirect(request.GET.get("next") or "club:control_dashboard")
        messages.error(request, "Login yoki parol noto'g'ri.")

    return render(request, "club/control/login.html")


def control_logout(request):
    logout(request)
    return redirect("club:control_login")


def percent(value, total):
    return round((value / total) * 100) if total else 0


def dashboard_context():
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    week_start = today - timedelta(days=6)
    month_start = today.replace(day=1)

    users = UserProfile.objects.all()
    active_users = users.filter(is_blocked=False)
    reports_today = DailyReport.objects.filter(date=today)
    reports_yesterday = DailyReport.objects.filter(date=yesterday)
    reports_week = DailyReport.objects.filter(date__gte=week_start)
    reports_month = DailyReport.objects.filter(date__gte=month_start)

    user_total = users.count()
    active_total = active_users.count()
    today_report_count = reports_today.count()
    today_xp = reports_today.aggregate(total=Sum("xp_earned"))["total"] or 0

    task_counts = DailyReport.objects.aggregate(
        wake_early=Count("id", filter=Q(wake_early=True)),
        prayer=Count("id", filter=Q(prayer=True)),
        sport=Count("id", filter=Q(sport=True)),
        book=Count("id", filter=Q(book=True)),
        goal_written=Count("id", filter=Q(goal_written=True)),
    )
    task_labels = {
        "wake_early": TaskCode.WAKE_EARLY.label,
        "prayer": TaskCode.PRAYER.label,
        "sport": TaskCode.SPORT.label,
        "book": TaskCode.BOOK.label,
        "goal_written": TaskCode.GOAL_WRITTEN.label,
    }
    max_task = max(task_counts.values()) if task_counts else 0

    daily_rows = []
    max_daily_xp = 0
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        day_reports = DailyReport.objects.filter(date=day)
        day_xp = day_reports.aggregate(total=Sum("xp_earned"))["total"] or 0
        max_daily_xp = max(max_daily_xp, day_xp)
        daily_rows.append({"date": day.strftime("%d.%m"), "xp": day_xp, "reports": day_reports.count()})
    for row in daily_rows:
        row["percent"] = percent(row["xp"], max_daily_xp)

    return {
        "today": today,
        "cards": [
            {"label": "Jami user", "value": user_total},
            {"label": "Aktiv user", "value": active_total},
            {"label": "Bugungi hisobot", "value": today_report_count},
            {"label": "Bugungi XP", "value": today_xp},
        ],
        "quick_stats": [
            {"label": "Bugungi qatnashuv", "value": f"{percent(today_report_count, active_total)}%"},
            {"label": "Kecha hisobot", "value": reports_yesterday.count()},
            {"label": "Haftalik XP", "value": reports_week.aggregate(total=Sum("xp_earned"))["total"] or 0},
            {"label": "Oylik XP", "value": reports_month.aggregate(total=Sum("xp_earned"))["total"] or 0},
        ],
        "tasks": [
            {"label": task_labels[key], "value": value, "percent": percent(value, max_task)}
            for key, value in task_counts.items()
        ],
        "daily_rows": daily_rows,
        "top_users": active_users.order_by("-xp", "joined_at")[:8],
        "latest_reports": DailyReport.objects.select_related("user").order_by("-created_at")[:8],
    }


@staff_required
def control_dashboard(request):
    return render(request, "club/control/dashboard.html", dashboard_context())


@staff_required
def control_users(request):
    query = request.GET.get("q", "").strip()
    users = UserProfile.objects.all()
    if query:
        users = users.filter(
            Q(full_name__icontains=query)
            | Q(username__icontains=query)
            | Q(region__icontains=query)
            | Q(telegram_id__icontains=query)
        )
    return render(
        request,
        "club/control/users.html",
        {
            "users": users.order_by("-xp", "joined_at")[:100],
            "query": query,
        },
    )


@staff_required
@require_http_methods(["GET", "POST"])
def control_user_detail(request, pk):
    profile = get_object_or_404(UserProfile, pk=pk)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "toggle_block":
            profile.is_blocked = not profile.is_blocked
            profile.save(update_fields=["is_blocked", "updated_at"])
            messages.success(request, "Foydalanuvchi holati yangilandi.")
        elif action == "xp_adjust":
            try:
                amount = int(request.POST.get("amount") or 0)
            except ValueError:
                messages.error(request, "XP miqdori faqat son bo'lishi kerak.")
                return redirect("club:control_user_detail", pk=profile.pk)
            if amount == 0:
                messages.error(request, "XP miqdori 0 bo'lmasligi kerak.")
                return redirect("club:control_user_detail", pk=profile.pk)
            note = request.POST.get("note", "").strip()
            profile.xp = max(0, profile.xp + amount)
            profile.save(update_fields=["xp", "updated_at"])
            XPTransaction.objects.create(
                user=profile,
                amount=amount,
                reason=XPTransaction.Reason.ADMIN_ADJUSTMENT,
                note=note or f"Custom admin: {request.user}",
            )
            messages.success(request, f"{amount} XP o'zgartirildi.")
        return redirect("club:control_user_detail", pk=profile.pk)

    return render(
        request,
        "club/control/user_detail.html",
        {
            "profile": profile,
            "reports": profile.reports.order_by("-date")[:20],
            "transactions": profile.xp_transactions.order_by("-created_at")[:20],
        },
    )


@staff_required
def control_reports(request):
    reports = DailyReport.objects.select_related("user").order_by("-date", "-created_at")[:150]
    return render(request, "club/control/reports.html", {"reports": reports})


@staff_required
@require_http_methods(["GET", "POST"])
def control_announcements(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        text = request.POST.get("text", "").strip()
        if title and text:
            Announcement.objects.create(title=title, text=text)
            messages.success(request, "E'lon saqlandi.")
            return redirect("club:control_announcements")
        messages.error(request, "Sarlavha va matn kerak.")

    return render(
        request,
        "club/control/announcements.html",
        {"announcements": Announcement.objects.order_by("-created_at")[:50]},
    )
