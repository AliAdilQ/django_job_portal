from django.urls import path
from . import views

app_name = "applications"
urlpatterns = [
    path("mine/", views.mine, name="mine"),
    path("received/", views.received, name="received"),
    path("apply/<int:job_pk>/", views.apply, name="apply"),
    path("profile-resume/", views.profile_resume, name="profile_resume"),
    path("profiles/<int:user_pk>/resume/", views.profile_resume, name="admin_profile_resume"),
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/resume/", views.resume, name="resume"),
]
