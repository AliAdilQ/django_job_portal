from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("jobs/", include("jobs.urls")),
    path("applications/", include("applications.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("", include("core.urls")),
]
# Resumes have their own authenticated download route; never expose MEDIA_ROOT.
if settings.DEBUG:
    urlpatterns += static("/media/photos/", document_root=settings.MEDIA_ROOT / "photos")
    urlpatterns += static("/media/logos/", document_root=settings.MEDIA_ROOT / "logos")
handler403 = "core.views.error_403"
handler404 = "core.views.error_404"
handler500 = "core.views.error_500"
