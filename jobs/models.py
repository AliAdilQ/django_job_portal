from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from accounts.models import Company, User


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=30, default="code")

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class JobQuerySet(models.QuerySet):
    def available(self):
        return self.filter(status="open", deadline__gte=timezone.localdate(), company__owner__is_active=True)


class Job(models.Model):
    class Type(models.TextChoices):
        FULL_TIME = "full_time", "Full Time"
        PART_TIME = "part_time", "Part Time"
        INTERNSHIP = "internship", "Internship"
        CONTRACT = "contract", "Contract"
        FREELANCE = "freelance", "Freelance"
        REMOTE = "remote", "Remote"

    class Level(models.TextChoices):
        ENTRY = "entry", "Entry Level"
        JUNIOR = "junior", "Junior"
        MID = "mid", "Mid Level"
        SENIOR = "senior", "Senior"
        LEAD = "lead", "Lead / Manager"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    title = models.CharField(max_length=180)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="jobs")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="jobs")
    description = models.TextField()
    requirements = models.TextField()
    responsibilities = models.TextField()
    skills = models.CharField(max_length=500)
    location = models.CharField(max_length=150)
    salary_min = models.PositiveIntegerField(help_text="Annual salary in USD.")
    salary_max = models.PositiveIntegerField(help_text="Annual salary in USD.")
    job_type = models.CharField(max_length=20, choices=Type.choices, default=Type.FULL_TIME)
    experience_level = models.CharField(max_length=10, choices=Level.choices, default=Level.MID)
    education = models.CharField(max_length=250, blank=True)
    remote = models.BooleanField(default=False)
    deadline = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    vacancies = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    featured = models.BooleanField(default=False)
    objects = JobQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [models.Index(fields=["status", "deadline"]), models.Index(fields=["category", "job_type"])]
        constraints = [
            models.CheckConstraint(condition=Q(salary_max__gte=models.F("salary_min")), name="valid_salary_range"),
            models.CheckConstraint(condition=Q(vacancies__gte=1), name="at_least_one_vacancy"),
        ]

    def clean(self):
        if self.salary_min is not None and self.salary_max is not None and self.salary_max < self.salary_min:
            raise ValidationError({"salary_max": "Maximum salary must be at least the minimum."})
        if self.vacancies is not None and self.vacancies < 1:
            raise ValidationError({"vacancies": "At least one vacancy is required."})

    @property
    def is_available(self):
        return self.status == self.Status.OPEN and self.deadline >= timezone.localdate() and self.company.owner.is_active

    @property
    def skill_list(self):
        return [s.strip() for s in self.skills.split(",") if s.strip()]

    def get_absolute_url(self):
        return reverse("jobs:detail", args=[self.pk])

    def __str__(self):
        return f"{self.title} at {self.company.name}"


class SavedJob(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_jobs")
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="saved_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "job"], name="unique_saved_job")]

    def __str__(self):
        return f"{self.user} saved {self.job}"
