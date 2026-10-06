from django import forms

from accounts.validators import validate_resume
from core.forms import StyledFormMixin
from .models import Application


class ApplicationForm(StyledFormMixin, forms.Form):
    resume = forms.FileField(required=False, validators=[validate_resume], widget=forms.FileInput(attrs={"accept": "application/pdf"}), help_text="PDF, up to 5 MB. Leave empty to use your profile resume.")
    cover_letter = forms.CharField(max_length=6000, widget=forms.Textarea(attrs={"rows": 7, "placeholder": "Tell the team why this opportunity feels like a great fit."}))

    def __init__(self, *args, profile_resume=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile_resume = profile_resume

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("resume") and not self.profile_resume:
            self.add_error("resume", "Upload a resume or add one to your profile first.")
        return cleaned


class StatusForm(StyledFormMixin, forms.Form):
    status = forms.ChoiceField(choices=Application.Status.choices)
