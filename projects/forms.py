from django import forms

from .models import Project


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
