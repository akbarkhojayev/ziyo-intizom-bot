from django.urls import path

from . import control_views, views


app_name = "club"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("app/", views.mini_app, name="mini_app"),
    path("control/login/", control_views.control_login, name="control_login"),
    path("control/logout/", control_views.control_logout, name="control_logout"),
    path("control/", control_views.control_dashboard, name="control_dashboard"),
    path("control/users/", control_views.control_users, name="control_users"),
    path("control/users/<int:pk>/", control_views.control_user_detail, name="control_user_detail"),
    path("control/reports/", control_views.control_reports, name="control_reports"),
    path("control/announcements/", control_views.control_announcements, name="control_announcements"),
    path("api/bootstrap/", views.api_bootstrap, name="api_bootstrap"),
    path("api/register/", views.api_register, name="api_register"),
    path("api/report/", views.api_submit_report, name="api_submit_report"),
    path("api/ranking/", views.api_ranking, name="api_ranking"),
    path("api/story-image/<int:telegram_id>.png", views.api_story_image, name="api_story_image_png"),
    path("api/story-image/", views.api_story_image, name="api_story_image"),
]
