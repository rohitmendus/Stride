from .models import Project


def workspace_navigation(request):
    match = request.resolver_match
    if match is None or (
        match.namespace not in ("projects", "tasks") and match.view_name != "core:home"
    ):
        return {}
    if not request.user.is_authenticated:
        return {}
    return {
        "sidebar_projects": Project.objects.filter(memberships__user=request.user)
        .only("pk", "title")
        .order_by("-updated_at", "pk")[:6]
    }
