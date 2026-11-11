from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import F, Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from .forms import ProjectForm
from .models import Project, ProjectMembership


def _projects_for(user):
    return (
        Project.objects.filter(memberships__user=user)
        .annotate(current_role=F("memberships__role"))
        .select_related("owner")
    )


@require_GET
@never_cache
def project_list(request):
    return render(
        request, "projects/index.html", {"projects": _projects_for(request.user)}
    )


@require_GET
@never_cache
def project_detail(request, pk):
    project = get_object_or_404(
        _projects_for(request.user).prefetch_related(
            Prefetch(
                "memberships",
                queryset=ProjectMembership.objects.select_related("user").order_by(
                    "joined_at", "pk"
                ),
            )
        ),
        pk=pk,
    )
    return render(request, "projects/detail.html", {"project": project})


@require_http_methods(["GET", "POST"])
@never_cache
def project_create(request):
    form = ProjectForm(
        request.POST if request.method == "POST" else None,
        instance=Project(owner=request.user),
    )
    if request.method == "POST" and form.is_valid():
        project = form.save()
        messages.success(request, "Project created. A fresh start.")
        return redirect("projects:detail", pk=project.pk)
    return render(
        request,
        "projects/form.html",
        {"form": form, "heading": "A fresh start.", "submit_label": "Create project"},
    )


@require_http_methods(["GET", "POST"])
@never_cache
@transaction.atomic
def project_edit(request, pk):
    projects = _projects_for(request.user)
    if request.method == "POST":
        projects = projects.select_for_update(of=("self",))
    project = get_object_or_404(projects, pk=pk)
    if project.current_role != ProjectMembership.Role.ADMIN:
        raise PermissionDenied
    form = ProjectForm(
        request.POST if request.method == "POST" else None, instance=project
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Project details updated.")
        return redirect("projects:detail", pk=project.pk)
    return render(
        request,
        "projects/form.html",
        {
            "form": form,
            "project": project,
            "heading": "A little fine-tuning.",
            "submit_label": "Save changes",
        },
    )


@require_http_methods(["GET", "POST"])
@never_cache
@transaction.atomic
def project_delete(request, pk):
    projects = _projects_for(request.user)
    if request.method == "POST":
        projects = projects.select_for_update(of=("self",))
    project = get_object_or_404(projects, pk=pk)
    if project.owner_id != request.user.pk:
        raise PermissionDenied
    if request.method == "POST":
        project.delete()
        messages.success(request, "Project deleted.")
        return redirect("core:home")
    return render(request, "projects/confirm_delete.html", {"project": project})
