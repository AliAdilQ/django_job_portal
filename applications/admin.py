from django import forms
from django.contrib import admin
from django.db import models
from django.urls import reverse
from django.utils.html import format_html
from .models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("applicant", "job", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("applicant__email", "job__title", "job__company__name")
    ordering = ("-created_at",)
    list_select_related = ("applicant", "job")
    formfield_overrides = {models.FileField: {"widget": forms.FileInput}}
    readonly_fields = ("resume_download",)

    @admin.display(description="Submitted resume")
    def resume_download(self, obj):
        if obj and obj.pk and obj.resume:
            return format_html('<a href="{}">Download resume securely</a>', reverse("applications:resume", args=[obj.pk]))
        return "No resume uploaded"
