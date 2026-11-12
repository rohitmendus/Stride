from django import forms
from django.contrib.auth import get_user_model

from .models import Project, ProjectMembership


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("title", "description", "deadline")
        widgets = {
            "title": forms.TextInput(
                attrs={"autofocus": True, "placeholder": "Give your project a name"}
            ),
            "description": forms.Textarea(
                attrs={"rows": 4, "placeholder": "What are you working towards?"}
            ),
            "deadline": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        }


class MemberRoleForm(forms.Form):
    role = forms.ChoiceField(choices=ProjectMembership.Role.choices, initial="member")


class AddMemberForm(MemberRoleForm):
    email = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={"placeholder": "teammate@example.com"}),
    )
    field_order = ("email", "role")

    def __init__(self, *args, project, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        self.selected_user = (
            get_user_model().objects.filter(email__iexact=email, is_active=True).first()
        )
        if self.selected_user is None:
            raise forms.ValidationError("No active account found with that email.")
        if self.project.memberships.filter(user=self.selected_user).exists():
            raise forms.ValidationError("This person is already a project member.")
        return email
