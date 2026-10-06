from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db import models
from django.urls import reverse
from django.utils.html import format_html

from .models import Company, Profile, User

admin.site.site_header = "Django Job Portal administration"
admin.site.site_title = "Job Portal Admin"
admin.site.index_title = "Manage your platform"


@admin.register(User)
class PortalUserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    fieldsets = UserAdmin.fieldsets + (("Portal", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Portal", {"fields": ("email", "role")}),)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "headline", "location")
    search_fields = ("user__email", "skills", "location")
    list_filter = ("location",)
    formfield_overrides = {models.FileField: {"widget": forms.FileInput}}
    readonly_fields = ("resume_download",)

    @admin.display(description="Current resume")
    def resume_download(self, obj):
        if obj and obj.resume:
            return format_html('<a href="{}">Download resume securely</a>', reverse("applications:admin_profile_resume", args=[obj.user_id]))
        return "No resume uploaded"


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "location", "industry")
    search_fields = ("name", "owner__email", "location")
    list_filter = ("industry", "location")
