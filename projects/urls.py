from django.urls import path

from . import views

app_name = "projects"
urlpatterns = [
    path("", views.project_list, name="index"),
    path("new/", views.project_create, name="create"),
    path("<int:pk>/", views.project_detail, name="detail"),
    path("<int:pk>/members/", views.project_members, name="members"),
    path("<int:pk>/settings/", views.project_settings, name="settings"),
    path("<int:pk>/edit/", views.project_edit, name="edit"),
    path("<int:pk>/delete/", views.project_delete, name="delete"),
]
