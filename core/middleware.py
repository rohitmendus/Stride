from django.contrib.auth.middleware import LoginRequiredMiddleware
from django.http import HttpResponse
from django.utils.cache import add_never_cache_headers


class AppLoginRequiredMiddleware(LoginRequiredMiddleware):
    def handle_no_permission(self, request, view_func):
        response = super().handle_no_permission(request, view_func)
        if request.headers.get("HX-Request") == "true":
            response = HttpResponse(headers={"HX-Redirect": response.url})
        add_never_cache_headers(response)
        return response
