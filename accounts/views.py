from django.contrib.auth import login
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.views import LoginView
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from .forms import EmailLoginForm, RegistrationForm
from .models import User


class SignInView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailLoginForm
    redirect_authenticated_user = True


@login_not_required
@sensitive_post_parameters("password1", "password2")
@never_cache
@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("core:home")
    form = RegistrationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
        except IntegrityError:
            if not User.objects.filter(
                email__iexact=form.cleaned_data["email"]
            ).exists():
                raise
            form.add_error("email", "An account with this email already exists.")
        else:
            login(request, user)
            return redirect("core:home")
    return render(request, "accounts/register.html", {"form": form})
