from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Profile, User
from accounts.permissions import role_required
from jobs.models import Job
from .forms import ApplicationForm, StatusForm
from .models import Application


@role_required(User.Role.SEEKER)
def apply(request, job_pk):
    job = get_object_or_404(Job.objects.select_related("company__owner"), pk=job_pk)
    existing = Application.objects.filter(job=job, applicant=request.user).first()
    if existing:
        messages.info(request, "You've already applied to this job.")
        return redirect("applications:detail", pk=existing.pk)
    if not job.is_available:
        messages.error(request, "This job is no longer accepting applications.")
        return redirect(job)
    profile, _ = Profile.objects.get_or_create(user=request.user)
    form = ApplicationForm(request.POST or None, request.FILES or None, profile_resume=profile.resume)
    if request.method == "POST" and form.is_valid():
        application = Application(job=job, applicant=request.user, cover_letter=form.cleaned_data["cover_letter"])
        resume = form.cleaned_data.get("resume")
        if resume:
            application.resume = resume
        else:
            try:
                with profile.resume.open("rb") as source:
                    application.resume.save("resume.pdf", ContentFile(source.read()), save=False)
            except (FileNotFoundError, OSError):
                form.add_error("resume", "Your profile resume is missing. Please upload it again.")
                return render(request, "applications/apply.html", {"form": form, "job": job, "profile": profile})
        try:
            with transaction.atomic():
                application.save()
        except IntegrityError:
            application.resume.delete(save=False)
            messages.info(request, "You've already applied to this job.")
            return redirect("applications:mine")
        messages.success(request, "Application sent. Good luck with your next chapter!")
        return redirect("applications:detail", pk=application.pk)
    return render(request, "applications/apply.html", {"form": form, "job": job, "profile": profile})


@role_required(User.Role.SEEKER)
def mine(request):
    applications = Application.objects.filter(applicant=request.user).select_related("job__company")
    return render(request, "applications/list.html", {"page_obj": Paginator(applications, 10).get_page(request.GET.get("page")), "employer_view": False})


@role_required(User.Role.EMPLOYER)
def received(request):
    applications = Application.objects.filter(job__company__owner=request.user).select_related("job__company", "applicant")
    if request.GET.get("status"):
        applications = applications.filter(status=request.GET["status"])
    if request.GET.get("job", "").isdigit():
        applications = applications.filter(job_id=request.GET["job"])
    return render(request, "applications/list.html", {
        "page_obj": Paginator(applications, 10).get_page(request.GET.get("page")), "employer_view": True,
        "statuses": Application.Status.choices, "jobs": Job.objects.filter(company__owner=request.user),
    })


def can_review(user, application):
    return user.is_staff or (user.role == User.Role.EMPLOYER and application.job.company.owner_id == user.pk)


@login_required
def detail(request, pk):
    application = get_object_or_404(Application.objects.select_related("job__company", "applicant"), pk=pk)
    reviewer = can_review(request.user, application)
    if not reviewer and application.applicant_id != request.user.pk:
        raise PermissionDenied
    status_form = StatusForm(request.POST or None, initial={"status": application.status})
    if request.method == "POST":
        if not reviewer:
            raise PermissionDenied
        if status_form.is_valid():
            application.status = status_form.cleaned_data["status"]
            application.save(update_fields=["status", "updated_at"])
            messages.success(request, "Application status updated.")
            return redirect("applications:detail", pk=pk)
    profile = Profile.objects.filter(user=application.applicant).first()
    return render(request, "applications/detail.html", {"application": application, "reviewer": reviewer, "status_form": status_form, "applicant_profile": profile})


@login_required
def resume(request, pk):
    application = get_object_or_404(Application.objects.select_related("job__company"), pk=pk)
    if not can_review(request.user, application) and application.applicant_id != request.user.pk:
        raise PermissionDenied
    return serve_resume(application.resume, f"application-{pk}-resume.pdf")


@login_required
def profile_resume(request, user_pk=None):
    if user_pk is not None and not request.user.is_staff:
        raise PermissionDenied
    profile = get_object_or_404(Profile, user_id=user_pk or request.user.pk)
    return serve_resume(profile.resume, "my-resume.pdf")


def serve_resume(file, filename):
    if not file:
        raise Http404("Resume not found.")
    try:
        response = FileResponse(file.open("rb"), as_attachment=True, filename=Path(filename).name, content_type="application/pdf")
    except (FileNotFoundError, OSError) as exc:
        raise Http404("Resume not found.") from exc
    response["Cache-Control"] = "private, no-store"
    return response
