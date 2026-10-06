from django.urls import path
from . import views

app_name = "jobs"
urlpatterns = [
    path("", views.job_list, name="list"),
    path("manage/", views.manage, name="manage"),
    path("new/", views.edit, name="create"),
    path("saved/", views.saved, name="saved"),
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/edit/", views.edit, name="edit"),
    path("<int:pk>/delete/", views.delete, name="delete"),
    path("<int:pk>/status/", views.toggle_status, name="toggle_status"),
    path("<int:pk>/save/", views.toggle_save, name="toggle_save"),
]
