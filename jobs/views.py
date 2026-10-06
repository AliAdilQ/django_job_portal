from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import Company, User
from accounts.permissions import role_required
from .forms import JobForm
from .models import Category, Job, SavedJob


def job_list(request):
    jobs = Job.objects.available().select_related("company", "category")
    params = request.GET
    if params.get("q"):
        query = params["q"].strip()
        jobs = jobs.filter(Q(title__icontains=query) | Q(description__icontains=query) | Q(skills__icontains=query) | Q(company__name__icontains=query))
    if params.get("location"):
        jobs = jobs.filter(location__icontains=params["location"].strip())
    for field in ("category", "job_type", "experience_level"):
        if params.get(field):
            lookup = "category__slug" if field == "category" else field
            jobs = jobs.filter(**{lookup: params[field]})
    if params.get("remote") == "1":
        jobs = jobs.filter(Q(remote=True) | Q(job_type=Job.Type.REMOTE))
    filter_errors = []
    amounts = {}
    for name in ("salary_min", "salary_max"):
        if params.get(name):
            try:
                amount = int(params[name])
                if not 0 <= amount <= 10000000:
                    raise ValueError
                amounts[name] = amount
            except ValueError:
                filter_errors.append("Salary filters must be whole numbers between 0 and 10,000,000.")
    if amounts.get("salary_min", 0) > amounts.get("salary_max", 10000000):
        filter_errors.append("Minimum salary cannot exceed maximum salary.")
    if not filter_errors:
        if "salary_min" in amounts:
            jobs = jobs.filter(salary_max__gte=amounts["salary_min"])
        if "salary_max" in amounts:
            jobs = jobs.filter(salary_min__lte=amounts["salary_max"])
    else:
        jobs = jobs.none()
    sort = params.get("sort", "newest")
    ordering = {"newest": "-created_at", "oldest": "created_at", "salary_high": "-salary_max", "salary_low": "salary_min"}
    jobs = jobs.order_by(ordering.get(sort, "-created_at"), "-pk")
    page = Paginator(jobs, 9).get_page(params.get("page"))
    query = params.copy()
    query.pop("page", None)
    return render(request, "jobs/list.html", {
        "page_obj": page, "categories": Category.objects.all(), "job_types": Job.Type.choices,
        "levels": Job.Level.choices, "query_string": query.urlencode(), "filter_errors": filter_errors,
    })


def detail(request, pk):
    job = get_object_or_404(Job.objects.select_related("company__owner", "category"), pk=pk)
    saved = applied = False
    if request.user.is_authenticated:
        saved = SavedJob.objects.filter(user=request.user, job=job).exists()
        applied = job.applications.filter(applicant=request.user).exists()
    similar = Job.objects.available().filter(category=job.category).exclude(pk=job.pk).select_related("company", "category")[:3]
    return render(request, "jobs/detail.html", {"job": job, "saved": saved, "applied": applied, "similar_jobs": similar})


@role_required(User.Role.EMPLOYER)
def manage(request):
    jobs = Job.objects.filter(company__owner=request.user).select_related("company", "category").annotate(application_count=Count("applications")).order_by("-created_at", "-pk")
    return render(request, "jobs/manage.html", {"page_obj": Paginator(jobs, 12).get_page(request.GET.get("page"))})


@role_required(User.Role.EMPLOYER)
def edit(request, pk=None):
    company = Company.objects.filter(owner=request.user).first()
    if not company:
        messages.info(request, "Create your company profile before posting a job.")
        return redirect("accounts:company")
    job = get_object_or_404(Job, pk=pk, company=company) if pk else None
    form = JobForm(request.POST or None, instance=job)
    if request.method == "POST" and form.is_valid():
        instance = form.save(commit=False)
        instance.company = company
        instance.save()
        messages.success(request, "Your job has been updated." if job else "Your new job is live.")
        return redirect("jobs:manage")
    return render(request, "jobs/form.html", {"form": form, "job": job})


@role_required(User.Role.EMPLOYER)
def delete(request, pk):
    job = get_object_or_404(Job, pk=pk, company__owner=request.user)
    if request.method == "POST":
        job.delete()
        messages.success(request, "Job deleted, including its applications and bookmarks.")
        return redirect("jobs:manage")
    return render(request, "jobs/delete.html", {"job": job})


@require_POST
@role_required(User.Role.EMPLOYER)
def toggle_status(request, pk):
    job = get_object_or_404(Job, pk=pk, company__owner=request.user)
    if job.status == Job.Status.CLOSED and job.deadline < timezone.localdate():
        messages.error(request, "Update the application deadline before reopening this job.")
    else:
        job.status = Job.Status.CLOSED if job.status == Job.Status.OPEN else Job.Status.OPEN
        job.save(update_fields=["status"])
        messages.success(request, f"Job {job.get_status_display().lower()}.")
    return redirect("jobs:manage")


@role_required(User.Role.SEEKER)
def saved(request):
    bookmarks = SavedJob.objects.filter(user=request.user).select_related("job__company", "job__category")
    return render(request, "jobs/saved.html", {"page_obj": Paginator(bookmarks, 9).get_page(request.GET.get("page"))})


@require_POST
@role_required(User.Role.SEEKER)
def toggle_save(request, pk):
    job = get_object_or_404(Job, pk=pk)
    bookmark, created = SavedJob.objects.get_or_create(user=request.user, job=job)
    if not created:
        bookmark.delete()
    messages.success(request, "Job saved to your collection." if created else "Job removed from saved jobs.")
    # Only use known internal destinations, never an untrusted redirect URL.
    return HttpResponseRedirect(reverse("jobs:saved") if request.POST.get("source") == "saved" else job.get_absolute_url())
