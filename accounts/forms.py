from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm

from .models import User


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
