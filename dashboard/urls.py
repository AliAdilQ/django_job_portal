from django.urls import path
from . import views

app_name = "dashboard"
urlpatterns = [
    path("", views.home, name="home"),
    path("seeker/", views.seeker, name="seeker"),
    path("employer/", views.employer, name="employer"),
    path("admin/", views.admin_dashboard, name="admin"),
    path("admin/<slug:resource>/", views.admin_manage, name="admin_manage"),
]
