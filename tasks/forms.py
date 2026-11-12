from django import forms
from django.contrib.auth import get_user_model

from .models import Task


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = (
            "title",
            "description",
            "assigned_to",
            "priority",
            "deadline",
            "status",
        )
        labels = {"assigned_to": "Assignee"}
        widgets = {
            "title": forms.TextInput(
                attrs={"autofocus": True, "placeholder": "What needs to get done?"}
            ),
            "description": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Add a little context…"}
            ),
            "deadline": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        }

    def __init__(self, *args, project, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = (
            get_user_model()
            .objects.filter(project_memberships__project=project, is_active=True)
            .order_by("email")
        )
        self.fields["assigned_to"].empty_label = "Unassigned"
        if not self.instance.pk and self.initial.get("deadline") is None:
            self.initial["deadline"] = project.deadline


class TaskMoveForm(forms.Form):
    status = forms.ChoiceField(choices=Task.Status.choices)
    before_id = forms.IntegerField(
        required=False, min_value=1, max_value=9_223_372_036_854_775_807
    )
