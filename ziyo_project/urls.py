from django.contrib import admin
from django.urls import include, path, re_path
from django.contrib.staticfiles import views as staticfiles_views
from club.admin_views import dashboard


urlpatterns = [
    path("admin/dashboard/", dashboard, name="admin_dashboard"),
    path("admin/", admin.site.urls),
    path("", include("club.urls")),
    re_path(r"^static/(?P<path>.*)$", staticfiles_views.serve, {"insecure": True}),
]
