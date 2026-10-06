from django.db import models

from accounts.models import User
from accounts.validators import resume_path, validate_resume
from jobs.models import Job


class Application(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        REVIEW = "review", "Under Review"
        SHORTLISTED = "shortlisted", "Shortlisted"
        INTERVIEW = "interview", "Interview"
        REJECTED = "rejected", "Rejected"
        HIRED = "hired", "Hired"

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name="applications")
    resume = models.FileField(upload_to=resume_path, validators=[validate_resume])
    cover_letter = models.TextField(max_length=6000)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["job", "applicant"], name="one_application_per_job")]

    def __str__(self):
        return f"{self.applicant.display_name} — {self.job.title}"
