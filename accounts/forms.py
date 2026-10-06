from uuid import uuid4

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from core.forms import StyledFormMixin, StyledModelForm
from .models import Company, Profile, User


class RegisterForm(StyledFormMixin, UserCreationForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "role", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ["first_name", "last_name", "email"]:
            self.fields[name].required = True

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account already uses this email address.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = f"member_{uuid4().hex}"
        if commit:
            user.save()
        return user


class LoginForm(StyledFormMixin, AuthenticationForm):
    username = forms.CharField(label="Email or username", widget=forms.TextInput(attrs={"autocomplete": "username", "placeholder": "you@example.com"}))


class ProfileForm(StyledModelForm):
    class Meta:
        model = Profile
        exclude = ["user"]
        widgets = {
            "photo": forms.FileInput(attrs={"accept": "image/png,image/jpeg,image/webp"}),
            "resume": forms.FileInput(attrs={"accept": "application/pdf"}),
        }


class UserDetailsForm(StyledModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("An account already uses this email.")
        return email


class CompanyForm(StyledModelForm):
    class Meta:
        model = Company
        exclude = ["owner", "created_at"]
        widgets = {"logo": forms.FileInput(attrs={"accept": "image/png,image/jpeg,image/webp"})}
