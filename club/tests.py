from datetime import timedelta
import json

from django.test import TestCase
from django.utils import timezone

from .models import DailyReport, RunSession, TaskCode, UserProfile


class DailyReportTests(TestCase):
    def setUp(self):
        self.user = UserProfile.objects.create(telegram_id=1, full_name="Tester")

    def test_report_adds_xp_and_streak(self):
        report = DailyReport.submit(
            self.user,
            [TaskCode.WAKE_EARLY, TaskCode.PRAYER, TaskCode.SPORT],
        )
        self.user.refresh_from_db()

        self.assertEqual(report.xp_earned, 60)
        self.assertEqual(self.user.xp, 60)
        self.assertEqual(self.user.streak, 1)

    def test_report_is_once_per_day(self):
        DailyReport.submit(self.user, [TaskCode.WAKE_EARLY])
        second = DailyReport.submit(self.user, [TaskCode.PRAYER])
        self.user.refresh_from_db()

        self.assertEqual(second.xp_earned, 20)
        self.assertEqual(self.user.xp, 20)
        self.assertEqual(DailyReport.objects.count(), 1)

    def test_streak_increments_on_consecutive_days(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        DailyReport.submit(self.user, [TaskCode.WAKE_EARLY], report_date=yesterday)
        DailyReport.submit(self.user, [TaskCode.PRAYER], report_date=timezone.localdate())
        self.user.refresh_from_db()

        self.assertEqual(self.user.streak, 2)

    def test_daily_xp_max_is_100(self):
        report = DailyReport.submit(
            self.user,
            [
                TaskCode.WAKE_EARLY,
                TaskCode.PRAYER,
                TaskCode.SPORT,
                TaskCode.BOOK,
                TaskCode.GOAL_WRITTEN,
            ],
        )

        self.assertEqual(report.xp_earned, 100)


class ReportApiTests(TestCase):
    def setUp(self):
        self.user = UserProfile.objects.create(telegram_id=2, full_name="Runner")

    def test_sport_requires_verified_gps_run(self):
        response = self.client.post(
            "/api/report/",
            data=json.dumps({"telegram_id": self.user.telegram_id, "tasks": [TaskCode.SPORT.value]}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "sport_gps_required")

    def test_sport_report_accepts_verified_gps_run(self):
        RunSession.objects.create(
            user=self.user,
            date=timezone.localdate(),
            status=RunSession.Status.VERIFIED,
            distance_m=1000,
            duration_s=500,
            avg_speed_kmh=7.2,
            samples_count=5,
        )

        response = self.client.post(
            "/api/report/",
            data=json.dumps({"telegram_id": self.user.telegram_id, "tasks": [TaskCode.SPORT.value]}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["report"]["xp_earned"], 20)
