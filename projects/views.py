from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.cache import patch_vary_headers
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from tasks.models import Task

from .forms import ProjectForm
from .models import Project, ProjectMembership


def _projects_for(user):
    return (
        Project.objects.filter(memberships__user=user)
        .annotate(current_role=F("memberships__role"))
        .select_related("owner")
    )


def _project_context(project, active_tab):
    memberships = list(
        project.memberships.select_related("user").order_by("joined_at", "pk")
    )
    return {
        "project": project,
        "active_tab": active_tab,
        "memberships": memberships,
        "member_avatars": memberships[:4],
        "extra_member_count": max(0, len(memberships) - 4),
    }


@require_GET
@never_cache
def project_list(request):
    return render(
        request, "projects/index.html", {"projects": _projects_for(request.user)}
    )


def _board_options(params=None):
    params = params or {}
    priority = params.get("priority", "")
    assignee = params.get("assignee", "")[:20]
    return {
        "q": params.get("q", "")[:200].strip(),
        "priority": priority if priority in Task.Priority.values else "",
        "assignee": assignee
        if assignee == "unassigned" or (assignee.isascii() and assignee.isdecimal())
        else "",
        "mine": "1" if params.get("mine") == "1" else "",
        "view": "list" if params.get("view") == "list" else "board",
        "workspace": "mine" if params.get("workspace") == "mine" else "",
    }


def _board_query(params=None):
    return urlencode(
        {
            key: value
            for key, value in _board_options(params).items()
            if value and not (key == "view" and value == "board")
        }
    )


def _board_context(project, user, params=None):
    context = _project_context(project, "board")
    options = _board_options(params)
    columns = {
        status: {"status": status, "label": label, "tasks": []}
        for status, label in Task.Status.choices
    }
    tasks = list(project.tasks.select_related("assigned_to"))
    visible = []
    today = timezone.localdate()
    for task in tasks:
        task.can_manage = (
            project.current_role == ProjectMembership.Role.ADMIN
            or user.pk in (task.created_by_id, task.assigned_to_id)
        )
        task.is_overdue = task.status != Task.Status.COMPLETED and task.deadline < today
        assignee = task.assigned_to
        task.assignee_label = (
            assignee.get_full_name() or assignee.email if assignee else "Unassigned"
        )
        task.assignee_initials = (
            (
                "".join(
                    part[0] for part in assignee.get_full_name().split()[:2]
                ).upper()
                or assignee.email[0].upper()
            )
            if assignee
            else "—"
        )
        task.avatar_color = (
            ("green", "peach", "blue")[assignee.pk % 3] if assignee else "gray"
        )
        if (
            options["q"].casefold()
            not in (f"{task.title} {task.description} STR-{task.pk:03d}").casefold()
        ):
            continue
        if options["priority"] and task.priority != options["priority"]:
            continue
        if options["assignee"] == "unassigned":
            if task.assigned_to_id is not None:
                continue
        elif options["assignee"] and str(task.assigned_to_id) != options["assignee"]:
            continue
        if options["mine"] and task.assigned_to_id != user.pk:
            continue
        visible.append(task)
        columns[task.status]["tasks"].append(task)
    board_url = reverse("projects:detail", args=[project.pk])

    def link(**changes):
        query = _board_query(options | changes)
        return f"{board_url}?{query}" if query else board_url

    context.update(
        columns=list(columns.values()),
        task_count=len(tasks),
        visible_count=len(visible),
        visible_tasks=visible,
        my_task_count=sum(task.assigned_to_id == user.pk for task in tasks),
        board_options=options,
        board_query=_board_query(options),
        board_url=board_url,
        board_link=link(view="board"),
        list_link=link(view="list"),
        clear_filters_link=link(priority="", assignee=""),
        priority_choices=Task.Priority.choices,
    )
    return context


def _my_tasks_context(user, params=None):
    options = _board_options(params) | {
        "workspace": "mine",
        "view": "list",
        "mine": "",
        "assignee": "",
    }
    tasks = list(
        Task.objects.filter(
            assigned_to=user, project__memberships__user=user
        ).select_related("project")
    )
    visible = []
    today = timezone.localdate()
    for task in tasks:
        if (
            options["q"].casefold()
            not in (
                f"{task.title} {task.description} STR-{task.pk:03d} {task.project.title}"
            ).casefold()
        ):
            continue
        if options["priority"] and task.priority != options["priority"]:
            continue
        task.is_overdue = task.status != Task.Status.COMPLETED and task.deadline < today
        task.assignee_label = user.get_full_name() or user.email
        visible.append(task)
    url = reverse("projects:my_tasks")
    return {
        "personal_workspace": True,
        "visible_tasks": visible,
        "task_count": len(tasks),
        "visible_count": len(visible),
        "board_options": options,
        "board_query": _board_query(options),
        "board_url": url,
        "priority_choices": Task.Priority.choices,
        "clear_filters_link": f"{url}?{_board_query(options | {'priority': '', 'assignee': ''})}",
    }


@require_GET
@never_cache
def my_tasks(request):
    partial = (
        request.headers.get("HX-Request") == "true"
        and request.headers.get("HX-Target") == "project-board"
    )
    response = render(
        request,
        "projects/partials/my_tasks.html" if partial else "projects/my_tasks.html",
        _my_tasks_context(request.user, request.GET),
    )
    patch_vary_headers(response, ("HX-Request", "HX-Target"))
    return response


@require_GET
@never_cache
def project_detail(request, pk):
    project = get_object_or_404(_projects_for(request.user), pk=pk)
    partial = (
        request.headers.get("HX-Request") == "true"
        and request.headers.get("HX-Target") == "project-board"
    )
    response = render(
        request,
        "projects/partials/board.html" if partial else "projects/detail.html",
        _board_context(project, request.user, request.GET),
    )
    patch_vary_headers(response, ("HX-Request", "HX-Target"))
    return response


@require_GET
@never_cache
def project_members(request, pk):
    project = get_object_or_404(_projects_for(request.user), pk=pk)
    return render(
        request, "projects/members.html", _project_context(project, "members")
    )


@require_GET
@never_cache
def project_settings(request, pk):
    project = get_object_or_404(_projects_for(request.user), pk=pk)
    return render(
        request, "projects/settings.html", _project_context(project, "settings")
    )


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
