from django.contrib import admin
from .models import Category, Job, SavedJob


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "category", "status", "featured", "deadline", "created_at")
    list_filter = ("status", "featured", "job_type", "experience_level", "category", "remote")
    search_fields = ("title", "company__name", "location", "skills")
    ordering = ("-created_at",)
    list_select_related = ("company", "category")


@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    list_display = ("user", "job", "created_at")
    search_fields = ("user__email", "job__title")
    list_filter = ("created_at",)
