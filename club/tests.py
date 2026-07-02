from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from .models import DailyReport, TaskCode, UserProfile


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
