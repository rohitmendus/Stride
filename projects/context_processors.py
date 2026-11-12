from tasks.models import Task

from .models import Project


def workspace_navigation(request):
    match = request.resolver_match
    if match is None or (
        match.namespace not in ("projects", "tasks")
        and match.view_name not in ("core:home", "core:dashboard")
    ):
        return {}
    if not request.user.is_authenticated:
        return {}

    initials = (
        "".join(part[0] for part in request.user.get_full_name().split()[:2]).upper()
        or request.user.email[0].upper()
    )
    return {
        "sidebar_user_initials": initials,
        "sidebar_my_task_count": Task.objects.filter(
            project__memberships__user=request.user,
            assigned_to=request.user,
        ).count(),
        "sidebar_projects": Project.objects.filter(memberships__user=request.user)
        .only("pk", "title")
        .order_by("-updated_at", "pk")[:6],
    }
