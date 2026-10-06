from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from accounts.models import Company, User
from applications.models import Application
from jobs.models import Category, Job


def home(request):
    jobs = Job.objects.available().select_related("company", "category")
    categories = Category.objects.annotate(job_count=Count("jobs", filter=Q(jobs__status="open", jobs__deadline__gte=timezone.localdate(), jobs__company__owner__is_active=True)))
    return render(request, "core/home.html", {
        "featured_jobs": jobs.filter(featured=True)[:3], "recent_jobs": jobs[:4], "categories": categories[:6],
        "companies": Company.objects.filter(owner__is_active=True)[:5],
        "job_count": jobs.count(), "company_count": Company.objects.filter(owner__is_active=True).count(),
        "candidate_count": User.objects.filter(role="seeker", is_staff=False, is_active=True).count(),
        "placement_count": Application.objects.filter(status="hired").count(),
    })


def categories(request):
    items = Category.objects.annotate(job_count=Count("jobs", filter=Q(jobs__status="open", jobs__deadline__gte=timezone.localdate(), jobs__company__owner__is_active=True)))
    return render(request, "core/categories.html", {"categories": items})


def companies(request):
    items = Company.objects.filter(owner__is_active=True).annotate(job_count=Count("jobs", filter=Q(jobs__status="open", jobs__deadline__gte=timezone.localdate())))
    if request.GET.get("q"):
        items = items.filter(Q(name__icontains=request.GET["q"]) | Q(industry__icontains=request.GET["q"]))
    return render(request, "core/companies.html", {"companies": items})


def company_detail(request, pk):
    company = get_object_or_404(Company, pk=pk, owner__is_active=True)
    jobs = company.jobs.available().select_related("company", "category")
    return render(request, "core/company_detail.html", {"company": company, "jobs": jobs})


def error_403(request, exception=None):
    return render(request, "core/error.html", {"code": "403", "heading": "This space isn't yours", "description": "Your account doesn't have permission to access this page."}, status=403)


def error_404(request, exception=None):
    return render(request, "core/error.html", {"code": "404", "heading": "A little off the career path", "description": "The page you're looking for has moved or doesn't exist."}, status=404)


def error_500(request):
    return render(request, "core/error.html", {"code": "500", "heading": "Something didn't go to plan", "description": "We're having trouble loading this page. Please try again shortly."}, status=500)
