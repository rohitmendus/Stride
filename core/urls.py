from django.urls import path

from . import notification_views, views

app_name = "core"
urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("notifications/", notification_views.notification_list, name="notifications"),
    path(
        "notifications/read-all/",
        notification_views.notification_read_all,
        name="notifications_read_all",
    ),
    path(
        "notifications/<int:pk>/open/",
        notification_views.notification_open,
        name="notification_open",
    ),
    path("health/", views.health, name="health"),
    path("connection/", views.connection_status, name="connection"),
]
