import json

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.cache import patch_vary_headers
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from core.notifications import task_assigned
from projects.models import ProjectMembership
from projects.views import (
    _board_context,
    _board_query,
    _my_tasks_context,
    _projects_for,
)

from .forms import TaskForm, TaskMoveForm
from .models import Task


def _is_modal(request):
    return (
        request.headers.get("HX-Request") == "true"
        and request.headers.get("HX-Target") == "task-dialog-content"
    )


def _project(request, project_pk):
    projects = _projects_for(request.user)
    if request.method == "POST":
        projects = projects.select_for_update(of=("self",))
    project = get_object_or_404(projects, pk=project_pk)
    if request.method == "POST":
        # Keep membership checks stable until the task write commits.
        memberships = list(project.memberships.select_for_update().order_by("pk"))
        actor = next(
            (
                membership
                for membership in memberships
                if membership.user_id == request.user.pk
            ),
            None,
        )
        if actor is None:
            raise Http404
        project.current_role = actor.role
    return project


def _task_url(request, name, *args):
    url = reverse(name, args=args)
    query = _board_query(request.GET)
    return f"{url}?{query}" if query else url


def _return_url(request, project):
    if request.GET.get("workspace") == "mine":
        return _task_url(request, "projects:my_tasks")
    return _task_url(request, "projects:detail", project.pk)


def _workspace(request, project):
    if request.GET.get("workspace") == "mine":
        return _my_tasks_context(
            request.user, request.GET
        ), "projects/partials/my_tasks.html"
    return _board_context(
        project, request.user, request.GET
    ), "projects/partials/board.html"


def _render_task(request, project, partial, **context):
    context.update(
        project=project,
        partial=partial,
        is_modal=_is_modal(request),
        board_query=_board_query(request.GET),
        return_url=_return_url(request, project),
    )
    response = render(
        request, partial if context["is_modal"] else "tasks/page.html", context
    )
    patch_vary_headers(response, ("HX-Request", "HX-Target"))
    return response


def _saved(
    request, project, task_id=None, *, deleted=False, created=False, status=None
):
    if deleted:
        message = "Task deleted"
    elif created:
        message = "Task added to the board"
    elif status:
        message = f"Moved to {Task.Status(status).label}"
    else:
        message = "Task updated"
    if not _is_modal(request):
        messages.success(request, message)
        return redirect(_return_url(request, project))
    context, template = _workspace(request, project)
    context["board_oob"] = True
    response = render(request, template, context)
    response["HX-Trigger-After-Swap"] = json.dumps(
        {"taskSaved": {"task_id": task_id, "message": message}}
    )
    return response


def _append_position(task):
    last = (
        task.project.tasks.filter(status=task.status)
        .exclude(pk=task.pk)
        .aggregate(last=Max("position"))["last"]
    )
    task.position = 0 if last is None else last + 1


def _task(request, project, pk):
    tasks = project.tasks.select_related("created_by", "assigned_to")
    if request.method == "POST":
        tasks = tasks.select_for_update(of=("self",))
    return get_object_or_404(tasks, pk=pk)


def _can_manage(user, project, task):
    return project.current_role == ProjectMembership.Role.ADMIN or user.pk in (
        task.created_by_id,
        task.assigned_to_id,
    )


def _edit_response(request, project, task, form):
    return _render_task(
        request,
        project,
        "tasks/partials/form.html",
        form=form,
        task=task,
        can_delete=True,
        heading="Task details",
        submit_label="Save changes",
        form_action=_task_url(request, "tasks:edit", project.pk, task.pk),
    )


@require_http_methods(["GET", "POST"])
@never_cache
@transaction.atomic
def task_create(request, project_pk):
    project = _project(request, project_pk)
    task = Task(project=project, created_by=request.user)
    if request.method == "GET" and request.GET.get("status") in Task.Status.values:
        task.status = request.GET["status"]
    form = TaskForm(
        request.POST if request.method == "POST" else None,
        project=project,
        instance=task,
    )
    if request.method == "POST" and form.is_valid():
        _append_position(task)
        task.save()
        task_assigned(task, request.user)
        return _saved(request, project, task.pk, created=True)
    return _render_task(
        request,
        project,
        "tasks/partials/form.html",
        form=form,
        task=task,
        heading="New task",
        submit_label="Create task",
        form_action=_task_url(request, "tasks:create", project.pk),
    )


@require_GET
@never_cache
def task_detail(request, project_pk, pk):
    project = _project(request, project_pk)
    task = _task(request, project, pk)
    if _can_manage(request.user, project, task):
        return _edit_response(
            request, project, task, TaskForm(project=project, instance=task)
        )
    return _render_task(
        request,
        project,
        "tasks/partials/detail.html",
        task=task,
        heading="Task details",
    )


@require_http_methods(["GET", "POST"])
@never_cache
@transaction.atomic
def task_edit(request, project_pk, pk):
    project = _project(request, project_pk)
    task = _task(request, project, pk)
    if not _can_manage(request.user, project, task):
        raise PermissionDenied
    previous_status = task.status
    previous_assignee_id = task.assigned_to_id
    form = TaskForm(
        request.POST if request.method == "POST" else None,
        project=project,
        instance=task,
    )
    if request.method == "POST" and form.is_valid():
        if task.status != previous_status:
            _append_position(task)
        task.save()
        task_assigned(task, request.user, previous_assignee_id)
        return _saved(
            request,
            project,
            task.pk,
            status=task.status if task.status != previous_status else None,
        )
    return _edit_response(request, project, task, form)


@require_http_methods(["GET", "POST"])
@never_cache
@transaction.atomic
def task_delete(request, project_pk, pk):
    project = _project(request, project_pk)
    task = _task(request, project, pk)
    if not _can_manage(request.user, project, task):
        raise PermissionDenied
    if request.method == "POST":
        task.delete()
        return _saved(request, project, deleted=True)
    return _render_task(
        request,
        project,
        "tasks/partials/confirm_delete.html",
        task=task,
        heading="Delete this task?",
        form_action=_task_url(request, "tasks:delete", project.pk, task.pk),
    )


@require_POST
@never_cache
@transaction.atomic
def task_move(request, project_pk, pk):
    project = _project(request, project_pk)
    task = _task(request, project, pk)
    if not _can_manage(request.user, project, task):
        raise PermissionDenied
    form = TaskMoveForm(request.POST)
    if not form.is_valid():
        return JsonResponse(
            {"error": "Choose a valid column and position."}, status=400
        )
    status = form.cleaned_data["status"]
    before_id = form.cleaned_data["before_id"]
    neighbors = list(
        project.tasks.select_for_update()
        .filter(status__in=(task.status, status))
        .exclude(pk=task.pk)
    )
    destination = [neighbor for neighbor in neighbors if neighbor.status == status]
    index = len(destination)
    if before_id is not None:
        index = next(
            (i for i, neighbor in enumerate(destination) if neighbor.pk == before_id),
            None,
        )
        if index is None:
            return JsonResponse(
                {"error": "The board changed. Refresh and try again."}, status=409
            )
    source = [neighbor for neighbor in neighbors if neighbor.status == task.status]
    previous_status = task.status
    task.status = status
    task.position = index
    try:
        task.save(update_fields={"status", "position", "updated_at"})
    except ValidationError:
        return JsonResponse(
            {"error": "Update the task details before moving it."}, status=400
        )
    destination.insert(index, task)
    changed = []
    columns = [destination] if previous_status == status else [source, destination]
    for column in columns:
        for position, neighbor in enumerate(column):
            if neighbor.position != position:
                neighbor.position = position
                changed.append(neighbor)
    # Only server-derived positions bypass model save hooks.
    Task.objects.bulk_update(changed, ["position"])
    if (
        request.headers.get("HX-Request") == "true"
        and request.headers.get("HX-Target") == "project-board"
    ):
        context, template = _workspace(request, project)
        response = render(request, template, context)
        response["HX-Trigger-After-Swap"] = json.dumps(
            {
                "taskMoved": {
                    "task_id": task.pk,
                    "message": f"Moved to {task.get_status_display()}",
                    "announcement": (
                        f"Task moved to {task.get_status_display()}, "
                        f"position {task.position + 1}."
                    ),
                }
            }
        )
        return response
    messages.success(request, "Task moved.")
    return redirect(_return_url(request, project))
