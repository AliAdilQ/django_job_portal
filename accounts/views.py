from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render

from .forms import CompanyForm, ProfileForm, RegisterForm, UserDetailsForm
from .models import Company, Profile, User
from .permissions import role_required


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save()
            Profile.objects.create(user=user)
        login(request, user, backend="accounts.backends.EmailOrUsernameBackend")
        messages.success(request, "Welcome! Let's make your next chapter happen.")
        return redirect("accounts:company" if user.role == User.Role.EMPLOYER else "accounts:profile")
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    instance, _ = Profile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, request.FILES or None, instance=instance)
    user_form = UserDetailsForm(request.POST or None, instance=request.user)
    if request.method == "POST":
        form_valid, user_valid = form.is_valid(), user_form.is_valid()
        if form_valid and user_valid:
            with transaction.atomic():
                user_form.save()
                form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"form": form, "user_form": user_form, "profile": instance})


@role_required(User.Role.EMPLOYER)
def company(request):
    instance = Company.objects.filter(owner=request.user).first()
    form = CompanyForm(request.POST or None, request.FILES or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        company = form.save(commit=False)
        company.owner = request.user
        company.save()
        messages.success(request, "Your company profile is ready.")
        return redirect("accounts:company")
    return render(request, "accounts/company.html", {"form": form, "company": instance})
