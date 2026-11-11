from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    BaseUserCreationForm,
    UserChangeForm,
)

from .models import User


class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(
            attrs={
                "autofocus": True,
                "autocomplete": "email",
                "placeholder": "you@example.com",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"autocomplete": "current-password", "placeholder": "Your password"}
        ),
    )
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Email or password is incorrect.",
    }


class AccountCreationForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")

    def clean_email(self):
        return User.objects.normalize_email(self.cleaned_data["email"])


class AccountChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"

    def clean_email(self):
        return User.objects.normalize_email(self.cleaned_data["email"])


class RegistrationForm(AccountCreationForm):
    first_name = forms.CharField(
        label="First name",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "autofocus": True,
                "autocomplete": "given-name",
                "placeholder": "Your first name",
            }
        ),
    )

    class Meta(AccountCreationForm.Meta):
        fields = ("first_name", "email")
        labels = {"email": "Email address"}
        widgets = {
            "email": forms.EmailInput(
                attrs={"autocomplete": "email", "placeholder": "you@example.com"}
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[
            "password1"
        ].help_text = "Use at least 10 characters, not just numbers."
        self.fields["password1"].widget.attrs["placeholder"] = "Create a password"
        self.fields["password2"].widget.attrs["placeholder"] = "Repeat your password"
        self.fields["password2"].help_text = ""
