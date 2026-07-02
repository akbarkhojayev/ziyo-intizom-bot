from django.contrib import admin, messages

from .models import (
    Achievement,
    Announcement,
    DailyReport,
    UserAchievement,
    UserProfile,
    XPTransaction,
)


@admin.action(description="Tanlangan foydalanuvchilarga 100 XP qo'shish")
def add_100_xp(modeladmin, request, queryset):
    for user in queryset:
        user.xp += 100
        user.save(update_fields=["xp", "updated_at"])
        XPTransaction.objects.create(
            user=user,
            amount=100,
            reason=XPTransaction.Reason.ADMIN_ADJUSTMENT,
            note=f"Admin: {request.user}",
        )
    messages.success(request, f"{queryset.count()} foydalanuvchiga XP qo'shildi.")


@admin.action(description="Tanlangan foydalanuvchilarni bloklash")
def block_users(modeladmin, request, queryset):
    updated = queryset.update(is_blocked=True)
    messages.success(request, f"{updated} foydalanuvchi bloklandi.")


@admin.action(description="Tanlangan foydalanuvchilarni blokdan chiqarish")
def unblock_users(modeladmin, request, queryset):
    updated = queryset.update(is_blocked=False)
    messages.success(request, f"{updated} foydalanuvchi blokdan chiqarildi.")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "telegram_id",
        "xp",
        "streak",
        "league_label",
        "main_goal",
        "region",
        "is_blocked",
        "joined_at",
    )
    list_filter = ("main_goal", "gender", "is_blocked", "joined_at")
    search_fields = ("full_name", "username", "telegram_id", "region", "referral_code")
    readonly_fields = ("joined_at", "updated_at", "referral_code", "league_label")
    list_per_page = 25
    date_hierarchy = "joined_at"
    fieldsets = (
        ("Telegram", {"fields": ("telegram_id", "username", "first_name")}),
        ("Profil", {"fields": ("full_name", "age", "gender", "region", "main_goal")}),
        ("Progress", {"fields": ("xp", "streak", "last_report_date", "league_label")}),
        ("Referral", {"fields": ("referral_code", "referred_by")}),
        ("Holat", {"fields": ("is_blocked", "joined_at", "updated_at")}),
    )
    actions = [add_100_xp, block_users, unblock_users]


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "xp_earned", "wake_early", "prayer", "sport", "book", "goal_written")
    list_filter = ("date", "wake_early", "prayer", "sport", "book", "goal_written")
    search_fields = ("user__full_name", "user__telegram_id")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("user",)
    date_hierarchy = "date"
    list_per_page = 30


@admin.register(XPTransaction)
class XPTransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "reason", "note", "created_at")
    list_filter = ("reason", "created_at")
    search_fields = ("user__full_name", "user__telegram_id", "note")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("user", "report")
    date_hierarchy = "created_at"
    list_per_page = 30


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "criteria", "threshold", "is_active")
    list_filter = ("criteria", "is_active")
    search_fields = ("name", "code", "description")
    prepopulated_fields = {"code": ("name",)}


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ("user", "achievement", "unlocked_at")
    list_filter = ("achievement", "unlocked_at")
    search_fields = ("user__full_name", "achievement__name")
    autocomplete_fields = ("user", "achievement")
    date_hierarchy = "unlocked_at"


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "is_sent", "created_at", "sent_at")
    list_filter = ("is_sent", "created_at")
    search_fields = ("title", "text")
    readonly_fields = ("created_at", "sent_at")
    list_per_page = 25


admin.site.site_header = "ZIYO | INTIZOM CLUB Admin"
admin.site.site_title = "ZIYO Admin"
admin.site.index_title = "Boshqaruv paneli"
