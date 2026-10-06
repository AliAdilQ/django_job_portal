from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower

from .validators import logo_path, photo_path, resume_path, validate_image, validate_resume


class User(AbstractUser):
    class Role(models.TextChoices):
        SEEKER = "seeker", "Job Seeker"
        EMPLOYER = "employer", "Employer"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.SEEKER)

    class Meta:
        constraints = [models.UniqueConstraint(Lower("email"), name="unique_email_case_insensitive")]

    def save(self, *args, **kwargs):
        self.email = self.email.lower().strip()
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return self.get_full_name() or self.username


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    photo = models.ImageField(upload_to=photo_path, validators=[validate_image], blank=True, help_text="JPG, PNG or WebP, up to 2 MB. Upload a new image to replace the current one.")
    headline = models.CharField(max_length=150, blank=True)
    skills = models.CharField(max_length=500, blank=True, help_text="Separate skills with commas.")
    education = models.TextField(blank=True)
    experience = models.TextField(blank=True)
    location = models.CharField(max_length=150, blank=True)
    bio = models.TextField(blank=True, max_length=1500)
    resume = models.FileField(upload_to=resume_path, validators=[validate_resume], blank=True, help_text="PDF, up to 5 MB. Upload a new resume to replace the current one.")

    @property
    def completion(self):
        fields = [self.photo, self.headline, self.skills, self.education, self.experience, self.location, self.bio, self.resume]
        return round(sum(bool(value) for value in fields) / len(fields) * 100)

    def __str__(self):
        return self.user.display_name


class Company(models.Model):
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name="company")
    name = models.CharField(max_length=150)
    logo = models.ImageField(upload_to=logo_path, validators=[validate_image], blank=True, help_text="JPG, PNG or WebP, up to 2 MB.")
    website = models.URLField(blank=True)
    description = models.TextField(max_length=4000)
    location = models.CharField(max_length=150)
    industry = models.CharField(max_length=100, blank=True)
    size = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
