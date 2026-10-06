from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = "core"
urlpatterns = [
    path("favicon.ico", RedirectView.as_view(url="/static/images/favicon.svg")),
    path("", views.home, name="home"),
    path("categories/", views.categories, name="categories"),
    path("companies/", views.companies, name="companies"),
    path("companies/<int:pk>/", views.company_detail, name="company_detail"),
]
