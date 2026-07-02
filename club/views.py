import json

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import Achievement, DailyReport, Goal, TaskCode, UserProfile
from .services import get_or_create_telegram_user, leaderboard, task_payload, today_stats
def landing(request):
    return redirect("club:mini_app")


def mini_app(request):
    return render(
        request,
        "club/mini_app.html",
        {
            "goals": Goal.choices,
            "tasks": task_payload(),
            "brand": "ZIYO | INTIZOM CLUB",
            "slogan": "Intizom motivatsiyadan kuchli.",
        },
    )


def user_payload(user: UserProfile):
    today = timezone.localdate()
    report = DailyReport.objects.filter(user=user, date=today).first()
    achievements = user.achievements.select_related("achievement")[:20]
    recent_reports = DailyReport.objects.filter(user=user).order_by("-date")[:45]
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "full_name": user.full_name,
        "age": user.age,
        "gender": user.gender,
        "region": user.region,
        "main_goal": user.main_goal,
        "main_goal_label": user.get_main_goal_display(),
        "xp": user.xp,
        "streak": user.streak,
        "league": user.league_label,
        "rank": user.ranking_position(),
        "joined_at": user.joined_at.strftime("%d.%m.%Y"),
        "joined_date": user.joined_at.date().isoformat(),
        "referral_code": user.referral_code,
        "referral_url": f"https://t.me/{settings.BOT_USERNAME}?start={user.referral_code}",
        "reported_today": bool(report),
        "today_report": report_payload(report) if report else None,
        "history": [report_payload(item) for item in recent_reports],
        "achievements": [
            {
                "name": item.achievement.name,
                "description": item.achievement.description,
                "unlocked_at": item.unlocked_at.strftime("%d.%m.%Y"),
            }
            for item in achievements
        ],
    }


def report_payload(report: DailyReport):
    selected = []
    for task in TaskCode:
        if getattr(report, task.value):
            selected.append({"code": task.value, "label": task.label})
    return {
        "date": report.date.isoformat(),
        "xp_earned": report.xp_earned,
        "tasks": selected,
    }


def parse_body(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return {}


def resolve_user(data):
    telegram_id = data.get("telegram_id")
    if not telegram_id:
        return None
    return UserProfile.objects.filter(telegram_id=telegram_id, is_blocked=False).first()


@csrf_exempt
@require_POST
def api_bootstrap(request):
    data = parse_body(request)
    telegram_id = data.get("telegram_id")
    if not telegram_id:
        return JsonResponse({"ok": False, "error": "telegram_id_required"}, status=400)

    user = get_or_create_telegram_user(
        telegram_id=int(telegram_id),
        first_name=data.get("first_name", ""),
        username=data.get("username", ""),
        referral_code=data.get("referral_code", ""),
    )
    Achievement.seed_defaults()
    return JsonResponse(
        {
            "ok": True,
            "user": user_payload(user),
            "tasks": task_payload(),
            "leaderboard": leaderboard(user=user),
            "stats": today_stats(),
        }
    )


@csrf_exempt
@require_POST
def api_register(request):
    data = parse_body(request)
    user = resolve_user(data)
    if not user:
        return JsonResponse({"ok": False, "error": "user_not_found"}, status=404)

    user.full_name = data.get("full_name", user.full_name).strip() or user.full_name
    user.age = int(data["age"]) if str(data.get("age", "")).isdigit() else user.age
    user.gender = data.get("gender", user.gender)
    user.region = data.get("region", user.region).strip()
    user.main_goal = data.get("main_goal", user.main_goal)
    user.save(update_fields=["full_name", "age", "gender", "region", "main_goal", "updated_at"])
    return JsonResponse({"ok": True, "user": user_payload(user)})


@csrf_exempt
@require_POST
def api_submit_report(request):
    data = parse_body(request)
    user = resolve_user(data)
    if not user:
        return JsonResponse({"ok": False, "error": "user_not_found"}, status=404)
    if DailyReport.objects.filter(user=user, date=timezone.localdate()).exists():
        return JsonResponse(
            {"ok": False, "error": "already_reported", "user": user_payload(user)},
            status=409,
        )

    report = DailyReport.submit(user, data.get("tasks", []))
    user.refresh_from_db()
    return JsonResponse(
        {
            "ok": True,
            "report": report_payload(report),
            "user": user_payload(user),
            "leaderboard": leaderboard(user=user),
            "stats": today_stats(),
        }
    )


@require_GET
def api_ranking(request):
    telegram_id = request.GET.get("telegram_id")
    user = UserProfile.objects.filter(telegram_id=telegram_id).first() if telegram_id else None
    return JsonResponse(
        {
            "ok": True,
            "all": leaderboard("all", user=user),
            "week": leaderboard("week", user=user),
            "month": leaderboard("month", user=user),
            "year": leaderboard("year", user=user),
        }
    )
