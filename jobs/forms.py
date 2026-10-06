from django import forms
from django.utils import timezone

from core.forms import StyledModelForm
from .models import Job


class JobForm(StyledModelForm):
    class Meta:
        model = Job
        exclude = ["company", "featured", "created_at"]
        widgets = {"deadline": forms.DateInput(attrs={"type": "date"})}

    def clean_deadline(self):
        deadline = self.cleaned_data["deadline"]
        if deadline < timezone.localdate():
            raise forms.ValidationError("Choose today or a future application deadline.")
        return deadline
