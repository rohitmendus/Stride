from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("projects/<int:project_pk>/tasks/", include("tasks.urls")),
    path("projects/", include("projects.urls")),
    path("", include("core.urls")),
]
