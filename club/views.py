import json
import math
from io import BytesIO

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.http import require_GET, require_POST, require_safe
from PIL import Image, ImageDraw, ImageFont

from .models import Achievement, DailyReport, Goal, RunSession, TaskCode, UserProfile
from .services import get_or_create_telegram_user, leaderboard, task_payload, today_stats


MIN_RUN_DISTANCE_M = 800
MIN_RUN_DURATION_S = 360
MIN_RUN_SPEED_KMH = 3
MAX_RUN_SPEED_KMH = 18
MAX_GPS_ACCURACY_M = 80
MAX_POINT_SPEED_KMH = 30
REGION_CHOICES = {
    "Toshkent shahri",
    "Toshkent viloyati",
    "Andijon",
    "Buxoro",
    "Farg'ona",
    "Jizzax",
    "Namangan",
    "Navoiy",
    "Qashqadaryo",
    "Qoraqalpog'iston",
    "Samarqand",
    "Sirdaryo",
    "Surxondaryo",
    "Xorazm",
}


def landing(request):
    return redirect("club:mini_app")


@xframe_options_exempt
def mini_app(request):
    return render(
        request,
        "club/mini_app.html",
        {
            "goals": Goal.choices,
            "tasks": task_payload(),
            "brand": "ZIYO | INTIZOM CLUB",
            "slogan": "Intizom motivatsiyadan kuchli.",
            "asset_version": "20260706-sport-tap-v3",
        },
    )


def story_font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def draw_wrapped(draw, text, xy, font, fill, max_width, line_gap=10):
    x, y = xy
    words = text.split()
    lines = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += draw.textbbox((0, 0), line, font=font)[3] + line_gap
    return y


def rounded_card(draw, box, fill, outline="#263244", width=2, radius=34):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def center_text(draw, box, text, font, fill):
    left, top, right, bottom = box
    bbox = draw.textbbox((0, 0), text, font=font)
    x = left + ((right - left) - (bbox[2] - bbox[0])) / 2
    y = top + ((bottom - top) - (bbox[3] - bbox[1])) / 2 - 4
    draw.text((x, y), text, font=font, fill=fill)


@require_safe
def api_story_image(request, telegram_id=None):
    telegram_id = telegram_id or request.GET.get("telegram_id")
    user = UserProfile.objects.filter(telegram_id=telegram_id, is_blocked=False).first() if telegram_id else None
    if not user:
        return JsonResponse({"ok": False, "error": "user_not_found"}, status=404)

    today = timezone.localdate()
    report = DailyReport.objects.filter(user=user, date=today).first()
    tasks = ", ".join(item["label"] for item in report_payload(report)["tasks"]) if report else "Bugungi hisobot kutilmoqda"
    xp = report.xp_earned if report else 0

    image = Image.new("RGB", (1080, 1920), "#07110d")
    draw = ImageDraw.Draw(image)
    for y in range(1920):
        green = 16 + int(y / 1920 * 28)
        blue = 18 + int(y / 1920 * 20)
        draw.line([(0, y), (1080, y)], fill=(7, green, blue))
    draw.ellipse((-230, -180, 430, 500), fill="#10351f")
    draw.ellipse((730, 80, 1280, 650), fill="#0d2b28")
    draw.ellipse((-180, 1280, 420, 1980), fill="#12321d")

    rounded_card(draw, (68, 72, 1012, 1848), "#101820", "#274033", 3, 58)
    draw.rounded_rectangle((68, 72, 1012, 360), radius=58, fill="#14231b")
    draw.text((118, 126), "ZIYO | INTIZOM CLUB", font=story_font(34, True), fill="#22c55e")
    draw.text((118, 190), "Bugungi natija", font=story_font(72, True), fill="#f8fafc")
    draw_wrapped(draw, user.full_name, (118, 292), story_font(42, True), "#cbd5e1", 830, 8)

    rounded_card(draw, (118, 430, 962, 820), "#0d2218", "#23563a", 3, 44)
    center_text(draw, (118, 462, 962, 610), f"+{xp}", story_font(160, True), "#22c55e")
    center_text(draw, (118, 620, 962, 710), "XP", story_font(62, True), "#bbf7d0")
    center_text(draw, (118, 725, 962, 790), "bugungi intizom balli", story_font(34), "#94a3b8")

    metric_cards = [
        ((118, 880, 382, 1078), "Streak", f"{user.streak}", "kun"),
        ((408, 880, 672, 1078), "Reyting", f"#{user.ranking_position()}", "o'rin"),
        ((698, 880, 962, 1078), "Liga", user.league_label, ""),
    ]
    for box, label, value, suffix in metric_cards:
        rounded_card(draw, box, "#151f2b", "#263244", 2, 34)
        left, top, right, _ = box
        draw.text((left + 34, top + 42), label, font=story_font(30, True), fill="#94a3b8")
        draw.text((left + 34, top + 92), value, font=story_font(45, True), fill="#f8fafc")
        if suffix:
            draw.text((right - 88, top + 108), suffix, font=story_font(24, True), fill="#64748b")

    draw.text((118, 1142), "Bajarilgan vazifalar", font=story_font(38, True), fill="#e5e7eb")
    task_items = report_payload(report)["tasks"] if report else []
    x, y = 118, 1215
    if task_items:
        for item in task_items:
            label = item["label"]
            text_bbox = draw.textbbox((0, 0), label, font=story_font(31, True))
            chip_width = min(820, text_bbox[2] - text_bbox[0] + 56)
            if x + chip_width > 962:
                x = 118
                y += 78
            draw.rounded_rectangle((x, y, x + chip_width, y + 58), radius=26, fill="#1d2b39")
            draw.text((x + 28, y + 12), label, font=story_font(31, True), fill="#d1fae5")
            x += chip_width + 18
    else:
        draw_wrapped(draw, tasks, (118, y), story_font(40), "#cbd5e1", 820, 12)

    rounded_card(draw, (118, 1548, 962, 1698), "#22c55e", "#22c55e", 1, 38)
    center_text(draw, (118, 1568, 962, 1638), "Intizom motivatsiyadan kuchli", story_font(42, True), "#052e16")
    center_text(draw, (118, 1635, 962, 1688), "har kun 1% yaxshi", story_font(30, True), "#14532d")
    draw.text((118, 1740), f"@{settings.BOT_USERNAME}", font=story_font(36, True), fill="#94a3b8")
    draw.text((118, 1790), "ZIYO bilan do'stlaringizni ham taklif qiling", font=story_font(28), fill="#64748b")

    output = BytesIO()
    image.save(output, format="PNG")
    response = HttpResponse(output.getvalue(), content_type="image/png")
    response["Cache-Control"] = "no-store"
    response["Access-Control-Allow-Origin"] = "*"
    return response


def user_payload(user: UserProfile):
    today = timezone.localdate()
    report = DailyReport.objects.filter(user=user, date=today).first()
    run = RunSession.objects.filter(user=user, date=today).order_by("-started_at").first()
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
        "run_today": run_payload(run) if run else None,
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


def run_payload(run: RunSession | None):
    if not run:
        return None
    return {
        "id": run.id,
        "status": run.status,
        "is_verified": run.is_verified,
        "distance_m": run.distance_m,
        "duration_s": run.duration_s,
        "avg_speed_kmh": round(run.avg_speed_kmh, 1),
        "samples_count": run.samples_count,
        "rejection_reason": run.rejection_reason,
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "rules": {
            "min_distance_m": MIN_RUN_DISTANCE_M,
            "min_duration_s": MIN_RUN_DURATION_S,
            "min_speed_kmh": MIN_RUN_SPEED_KMH,
            "max_speed_kmh": MAX_RUN_SPEED_KMH,
        },
    }


def haversine_m(lat1, lon1, lat2, lon2):
    radius_m = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius_m * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def parse_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def verify_run(run: RunSession):
    now = timezone.now()
    duration_s = max(0, int((now - run.started_at).total_seconds()))
    avg_speed_kmh = (run.distance_m / duration_s) * 3.6 if duration_s else 0
    reasons = []
    if run.distance_m < MIN_RUN_DISTANCE_M:
        reasons.append(f"kamida {MIN_RUN_DISTANCE_M} metr kerak")
    if duration_s < MIN_RUN_DURATION_S:
        reasons.append(f"kamida {MIN_RUN_DURATION_S // 60} daqiqa kerak")
    if avg_speed_kmh < MIN_RUN_SPEED_KMH:
        reasons.append("tezlik juda past")
    if avg_speed_kmh > MAX_RUN_SPEED_KMH:
        reasons.append("tezlik juda yuqori")
    if run.samples_count < 3:
        reasons.append("GPS nuqtalari yetarli emas")

    run.finished_at = now
    run.duration_s = duration_s
    run.avg_speed_kmh = avg_speed_kmh
    run.status = RunSession.Status.REJECTED if reasons else RunSession.Status.VERIFIED
    run.rejection_reason = ", ".join(reasons)
    run.save(update_fields=["finished_at", "duration_s", "avg_speed_kmh", "status", "rejection_reason"])
    return run


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
    region = data.get("region", user.region).strip()
    user.region = region if region in REGION_CHOICES else user.region
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

    tasks = data.get("tasks", [])
    if TaskCode.SPORT.value in tasks and not RunSession.objects.filter(
        user=user,
        date=timezone.localdate(),
        status=RunSession.Status.VERIFIED,
    ).exists():
        return JsonResponse(
            {
                "ok": False,
                "error": "sport_gps_required",
                "message": "Sport vazifasi uchun avval GPS orqali yugurishni tasdiqlang.",
                "user": user_payload(user),
            },
            status=400,
        )

    report = DailyReport.submit(user, tasks)
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


@csrf_exempt
@require_POST
def api_run_start(request):
    data = parse_body(request)
    user = resolve_user(data)
    if not user:
        return JsonResponse({"ok": False, "error": "user_not_found"}, status=404)
    today = timezone.localdate()
    active = RunSession.objects.filter(user=user, date=today, status=RunSession.Status.ACTIVE).first()
    if active:
        return JsonResponse({"ok": True, "run": run_payload(active)})
    run = RunSession.objects.create(user=user, date=today)
    return JsonResponse({"ok": True, "run": run_payload(run)})


@csrf_exempt
@require_POST
def api_run_point(request):
    data = parse_body(request)
    user = resolve_user(data)
    if not user:
        return JsonResponse({"ok": False, "error": "user_not_found"}, status=404)
    run = RunSession.objects.filter(user=user, id=data.get("run_id"), status=RunSession.Status.ACTIVE).first()
    if not run:
        return JsonResponse({"ok": False, "error": "active_run_not_found"}, status=404)

    lat = parse_float(data.get("latitude"))
    lon = parse_float(data.get("longitude"))
    accuracy = parse_float(data.get("accuracy"))
    if lat is None or lon is None:
        return JsonResponse({"ok": False, "error": "location_required"}, status=400)
    if accuracy is not None and accuracy > MAX_GPS_ACCURACY_M:
        return JsonResponse({"ok": True, "run": run_payload(run), "ignored": "low_accuracy"})

    now = timezone.now()
    if run.last_latitude is not None and run.last_longitude is not None:
        step_m = haversine_m(run.last_latitude, run.last_longitude, lat, lon)
        seconds = max(1, int((now - (run.last_recorded_at or run.started_at)).total_seconds()))
        step_speed_kmh = (step_m / seconds) * 3.6
        if 2 <= step_m <= 300 and step_speed_kmh <= MAX_POINT_SPEED_KMH:
            run.distance_m += int(step_m)

    run.last_latitude = lat
    run.last_longitude = lon
    run.last_recorded_at = now
    run.samples_count += 1
    run.save(
        update_fields=[
            "last_latitude",
            "last_longitude",
            "last_recorded_at",
            "distance_m",
            "samples_count",
        ]
    )
    return JsonResponse({"ok": True, "run": run_payload(run)})


@csrf_exempt
@require_POST
def api_run_finish(request):
    data = parse_body(request)
    user = resolve_user(data)
    if not user:
        return JsonResponse({"ok": False, "error": "user_not_found"}, status=404)
    run = RunSession.objects.filter(user=user, id=data.get("run_id"), status=RunSession.Status.ACTIVE).first()
    if not run:
        return JsonResponse({"ok": False, "error": "active_run_not_found"}, status=404)
    run = verify_run(run)
    user.refresh_from_db()
    return JsonResponse({"ok": True, "run": run_payload(run), "user": user_payload(user)})


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
