from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import redirect, render

from accounts.models import Company, Profile, User
from accounts.permissions import role_required, staff_required
from applications.models import Application
from jobs.models import Category, Job, SavedJob


def status_statistics(queryset):
    counts = dict(queryset.values_list("status").annotate(total=Count("pk")))
    total = sum(counts.values()) or 1
    return [{"label": label, "key": key, "count": counts.get(key, 0), "width": round(counts.get(key, 0) / total * 100)} for key, label in Application.Status.choices]


@login_required
def home(request):
    if request.user.is_staff:
        return redirect("dashboard:admin")
    return redirect("dashboard:employer" if request.user.role == User.Role.EMPLOYER else "dashboard:seeker")


@role_required(User.Role.SEEKER)
def seeker(request):
    applications = request.user.applications.select_related("job__company")
    profile, _ = Profile.objects.get_or_create(user=request.user)
    stats = [
        ("Applications", applications.count(), "send"),
        ("Pending", applications.filter(status="pending").count(), "clock"),
        ("Shortlisted", applications.filter(status="shortlisted").count(), "star"),
        ("Interviews", applications.filter(status="interview").count(), "chat"),
        ("Saved jobs", request.user.saved_jobs.count(), "bookmark"),
    ]
    return render(request, "dashboard/seeker.html", {
        "stats": stats, "recent_applications": applications[:5], "profile": profile,
        "recommended_jobs": Job.objects.available().exclude(applications__applicant=request.user).select_related("company", "category")[:3],
    })


@role_required(User.Role.EMPLOYER)
def employer(request):
    jobs = Job.objects.filter(company__owner=request.user).select_related("company", "category").annotate(application_count=Count("applications")).order_by("-created_at", "-pk")
    applications = Application.objects.filter(job__company__owner=request.user).select_related("job", "applicant")
    stats = [
        ("Jobs posted", jobs.count(), "briefcase"), ("Active jobs", jobs.available().count(), "activity"),
        ("Applications", applications.count(), "send"), ("Shortlisted", applications.filter(status="shortlisted").count(), "star"),
        ("Hired", applications.filter(status="hired").count(), "check"),
    ]
    return render(request, "dashboard/employer.html", {"stats": stats, "recent_jobs": jobs[:4], "recent_applications": applications[:5], "status_statistics": status_statistics(applications)})


@staff_required
def admin_dashboard(request):
    stats = [
        ("Total users", User.objects.count(), "users"), ("Job seekers", User.objects.filter(role="seeker", is_staff=False).count(), "user"),
        ("Employers", User.objects.filter(role="employer", is_staff=False).count(), "briefcase"), ("Companies", Company.objects.count(), "building"),
        ("Total jobs", Job.objects.count(), "layers"), ("Active jobs", Job.objects.available().count(), "activity"),
        ("Applications", Application.objects.count(), "send"),
    ]
    return render(request, "dashboard/admin.html", {
        "stats": stats, "recent_users": User.objects.order_by("-date_joined")[:5],
        "recent_jobs": Job.objects.select_related("company")[:5],
        "recent_applications": Application.objects.select_related("job__company", "applicant")[:5],
        "status_statistics": status_statistics(Application.objects.all()),
    })


@staff_required
def admin_manage(request, resource):
    resources = {
        "users": (User, "Users", "accounts_user", ["email", "first_name", "last_name"]),
        "companies": (Company, "Companies", "accounts_company", ["name", "location"]),
        "jobs": (Job, "Jobs", "jobs_job", ["title", "company__name"]),
        "applications": (Application, "Applications", "applications_application", ["applicant__email", "job__title"]),
        "categories": (Category, "Categories", "jobs_category", ["name"]),
        "saved-jobs": (SavedJob, "Saved jobs", "jobs_savedjob", ["user__email", "job__title"]),
    }
    if resource not in resources:
        raise Http404
    model, title, admin_name, fields = resources[resource]
    objects = model.objects.all().order_by("-pk")
    if request.GET.get("q"):
        query = Q()
        for field in fields:
            query |= Q(**{f"{field}__icontains": request.GET["q"]})
        objects = objects.filter(query)
    return render(request, "dashboard/admin_manage.html", {
        "title": title, "resource": resource, "admin_name": admin_name,
        "page_obj": Paginator(objects, 15).get_page(request.GET.get("page")),
    })
