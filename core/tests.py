"""Critical workflows and privacy boundaries, using an isolated test database."""
from datetime import timedelta
from io import BytesIO, StringIO
from tempfile import TemporaryDirectory

from django.core import mail
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from accounts.models import Company, Profile, User
from applications.models import Application
from core.demo import resume_pdf
from jobs.models import Category, Job, SavedJob


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class PortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.seeker = User.objects.create_user("seeker", "seeker@example.com", "StrongPass123!", first_name="Amelia")
        cls.other_seeker = User.objects.create_user("other", "other@example.com", "StrongPass123!")
        cls.employer = User.objects.create_user("employer", "employer@example.com", "StrongPass123!", role="employer")
        cls.other_employer = User.objects.create_user("employer2", "employer2@example.com", "StrongPass123!", role="employer")
        cls.admin = User.objects.create_superuser("admin", "admin@example.com", "StrongPass123!")
        cls.company = Company.objects.create(owner=cls.employer, name="NovaTech", location="Austin", description="Thoughtful software.")
        cls.other_company = Company.objects.create(owner=cls.other_employer, name="PixelForge", location="New York", description="Great design.")
        cls.category = Category.objects.create(name="Software Development", slug="software-development")
        cls.job = Job.objects.create(title="Python Developer", company=cls.company, category=cls.category, description="Build useful tools.", requirements="Python", responsibilities="Develop software.", skills="Python, Django", location="Austin", salary_min=80000, salary_max=110000, deadline=timezone.localdate()+timedelta(days=30), remote=True)
        Profile.objects.create(user=cls.seeker)

    def setUp(self):
        self.media = TemporaryDirectory(dir=settings.BASE_DIR, prefix=".test-media-")
        self.settings_override = override_settings(MEDIA_ROOT=self.media.name)
        self.settings_override.enable()
        self.addCleanup(self.media.cleanup)
        self.addCleanup(self.settings_override.disable)

    def pdf(self):
        return SimpleUploadedFile("resume.pdf", resume_pdf("Amelia Khan", "Python developer"), content_type="application/pdf")

    def apply(self, user=None):
        self.client.force_login(user or self.seeker)
        return self.client.post(reverse("applications:apply", args=[self.job.pk]), {"resume": self.pdf(), "cover_letter": "I would love to bring my Python experience to your team."})

    def job_data(self, **changes):
        data = {"title": "Django Developer", "category": self.category.pk, "description": "Build useful tools.", "requirements": "Django experience", "responsibilities": "Deliver reliable code.", "skills": "Django, Python", "location": "Austin", "salary_min": 70000, "salary_max": 100000, "job_type": "full_time", "experience_level": "mid", "deadline": (timezone.localdate()+timedelta(days=30)).isoformat(), "vacancies": 2, "status": "open"}
        data.update(changes)
        return data

    def test_registration_and_email_login(self):
        response = self.client.post(reverse("accounts:register"), {"first_name": "Mia", "last_name": "Taylor", "email": "MIA@EXAMPLE.COM", "role": "seeker", "password1": "CareerNext456!", "password2": "CareerNext456!"})
        self.assertRedirects(response, reverse("accounts:profile"))
        user = User.objects.get(email="mia@example.com")
        self.assertTrue(user.check_password("CareerNext456!"))
        self.assertTrue(Profile.objects.filter(user=user).exists())
        self.client.post(reverse("accounts:logout"))
        response = self.client.post(reverse("accounts:login"), {"username": "MIA@example.com", "password": "CareerNext456!"})
        self.assertRedirects(response, reverse("dashboard:home"), fetch_redirect_response=False)

    def test_employer_registration_and_company_onboarding(self):
        response = self.client.post(reverse("accounts:register"), {"first_name": "Olivia", "last_name": "Bennett", "email": "new@example.com", "role": "employer", "password1": "CareerNext456!", "password2": "CareerNext456!"})
        self.assertRedirects(response, reverse("accounts:company"))
        response = self.client.post(reverse("accounts:company"), {"name": "New Team", "description": "A collaborative team.", "location": "Boston"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Company.objects.filter(name="New Team").exists())

    def test_invalid_registration_and_duplicate_email(self):
        for email, role in [("SEEKER@example.com", "seeker"), ("new@example.com", "admin")]:
            response = self.client.post(reverse("accounts:register"), {"first_name": "Mia", "last_name": "Taylor", "email": email, "role": role, "password1": "CareerNext456!", "password2": "CareerNext456!"})
            self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 5)

    def test_authentication_failure_and_required_routes(self):
        self.assertEqual(self.client.get(reverse("dashboard:seeker")).status_code, 302)
        response = self.client.post(reverse("accounts:login"), {"username": "seeker@example.com", "password": "wrong"})
        self.assertContains(response, "Please enter a correct")
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)

    def test_role_restrictions(self):
        self.client.force_login(self.seeker)
        for name in ["dashboard:employer", "dashboard:admin", "jobs:create", "jobs:manage", "applications:received", "accounts:company"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)
        self.client.force_login(self.employer)
        for name in ["dashboard:seeker", "applications:mine", "jobs:saved", "dashboard:admin"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)

    def test_employer_job_creation_and_validation(self):
        self.client.force_login(self.employer)
        response = self.client.post(reverse("jobs:create"), self.job_data(company=self.other_company.pk, featured="on"))
        self.assertRedirects(response, reverse("jobs:manage"))
        job = Job.objects.get(title="Django Developer")
        self.assertEqual(job.company, self.company)
        self.assertFalse(job.featured)
        for data in [self.job_data(salary_max=1), self.job_data(vacancies=0), self.job_data(deadline="2020-01-01")]:
            self.assertEqual(self.client.post(reverse("jobs:create"), data).status_code, 200)
        self.assertEqual(Job.objects.count(), 2)

    def test_own_job_edit_close_reopen_delete(self):
        self.client.force_login(self.employer)
        self.assertEqual(self.client.post(reverse("jobs:edit", args=[self.job.pk]), self.job_data(title="Updated role")).status_code, 302)
        self.job.refresh_from_db()
        self.assertEqual(self.job.title, "Updated role")
        url = reverse("jobs:toggle_status", args=[self.job.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "closed")
        self.client.post(url)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "open")
        self.client.get(reverse("jobs:delete", args=[self.job.pk]))
        self.assertTrue(Job.objects.filter(pk=self.job.pk).exists())
        self.client.post(reverse("jobs:delete", args=[self.job.pk]))
        self.assertFalse(Job.objects.filter(pk=self.job.pk).exists())

    def test_unauthorized_job_changes(self):
        self.client.force_login(self.other_employer)
        for name in ["jobs:edit", "jobs:delete", "jobs:toggle_status"]:
            self.assertEqual(self.client.post(reverse(name, args=[self.job.pk]), self.job_data()).status_code, 404)
        self.job.refresh_from_db()
        self.assertEqual(self.job.title, "Python Developer")

    def test_apply_duplicate_and_database_constraint(self):
        self.assertEqual(self.apply().status_code, 302)
        application = Application.objects.get()
        self.assertEqual(application.status, "pending")
        self.assertEqual(self.apply().status_code, 302)
        self.assertEqual(Application.objects.count(), 1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Application.objects.create(job=self.job, applicant=self.seeker, resume="resume.pdf", cover_letter="Duplicate")

    def test_profile_resume_snapshot(self):
        profile = self.seeker.profile
        profile.resume.save("profile.pdf", self.pdf())
        self.client.force_login(self.seeker)
        response = self.client.post(reverse("applications:apply", args=[self.job.pk]), {"cover_letter": "Use my profile resume."})
        self.assertEqual(response.status_code, 302)
        application = Application.objects.get()
        self.assertNotEqual(profile.resume.name, application.resume.name)
        with application.resume.open("rb") as submitted, profile.resume.open("rb") as original:
            self.assertEqual(submitted.read(), original.read())

    def test_closed_and_expired_jobs_reject_applications(self):
        for updates in [{"status": "closed"}, {"status": "open", "deadline": timezone.localdate()-timedelta(days=1)}]:
            Job.objects.filter(pk=self.job.pk).update(**updates)
            self.assertEqual(self.apply().status_code, 302)
        self.assertEqual(Application.objects.count(), 0)

    def test_resume_validation_and_required_resume(self):
        self.client.force_login(self.seeker)
        url = reverse("applications:apply", args=[self.job.pk])
        for resume in [None, SimpleUploadedFile("resume.exe", b"bad"), SimpleUploadedFile("fake.pdf", b"not a pdf"), SimpleUploadedFile("huge.pdf", b"%PDF-"+b"x"*(5*1024*1024))]:
            data = {"cover_letter": "Hello team."}
            if resume:
                data["resume"] = resume
            self.assertEqual(self.client.post(url, data).status_code, 200)
        self.assertEqual(Application.objects.count(), 0)

    def test_private_application_and_resume_permissions(self):
        self.apply()
        application = Application.objects.get()
        for user in [self.other_seeker, self.other_employer]:
            self.client.force_login(user)
            for name in ["applications:detail", "applications:resume"]:
                self.assertEqual(self.client.get(reverse(name, args=[application.pk])).status_code, 403)
        self.client.force_login(self.employer)
        response = self.client.get(reverse("applications:resume", args=[application.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        response.close()
        self.assertEqual(self.client.get("/media/"+application.resume.name).status_code, 404)

    def test_status_update_and_both_dashboards(self):
        self.apply()
        application = Application.objects.get()
        url = reverse("applications:detail", args=[application.pk])
        self.assertEqual(self.client.post(url, {"status": "hired"}).status_code, 403)
        self.client.force_login(self.employer)
        self.assertEqual(self.client.post(url, {"status": "made-up"}).status_code, 200)
        self.assertEqual(self.client.post(url, {"status": "interview"}).status_code, 302)
        self.assertContains(self.client.get(reverse("dashboard:employer")), "Python Developer")
        self.client.force_login(self.seeker)
        self.assertContains(self.client.get(reverse("dashboard:seeker")), "Interview")
        self.assertContains(self.client.get(reverse("applications:mine")), "Python Developer")

    def test_staff_profile_resume_download_and_admin_links(self):
        profile = self.seeker.profile
        profile.resume.save("profile.pdf", self.pdf())
        url = reverse("applications:admin_profile_resume", args=[self.seeker.pk])
        for user in [self.seeker, self.employer]:
            self.client.force_login(user)
            self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        response.close()
        response = self.client.get(reverse("admin:accounts_profile_change", args=[profile.pk]))
        self.assertContains(response, "Download resume securely")
        self.assertNotContains(response, 'href="/media/resumes/')

    def test_saved_jobs_and_post_only_actions(self):
        self.client.force_login(self.seeker)
        url = reverse("jobs:toggle_save", args=[self.job.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url)
        self.assertEqual(SavedJob.objects.count(), 1)
        self.assertContains(self.client.get(reverse("jobs:saved")), "Python Developer")
        self.client.post(url, {"source": "saved"})
        self.assertEqual(SavedJob.objects.count(), 0)

    def test_search_filters_sorting_and_pagination(self):
        for index in range(15):
            self.job.pk = None
            self.job.title = f"Designer {index}"
            self.job.salary_min = 30000+index*1000
            self.job.save()
        url = reverse("jobs:list")
        self.assertEqual(self.client.get(url).context["page_obj"].paginator.count, 16)
        self.assertEqual(len(self.client.get(url, {"page": 2}).context["page_obj"]), 7)
        for params in [{"q": "Python"}, {"location": "Austin"}, {"category": self.category.slug}, {"job_type": "full_time"}, {"experience_level": "mid"}, {"remote": "1"}, {"salary_min": "75000", "salary_max": "90000"}]:
            self.assertGreater(self.client.get(url, params).context["page_obj"].paginator.count, 0, params)
        self.assertEqual(self.client.get(url, {"q": "no-matching-role"}).context["page_obj"].paginator.count, 0)
        self.assertEqual(self.client.get(url, {"salary_min": "nonsense"}).context["page_obj"].paginator.count, 0)
        page = self.client.get(url, {"sort": "salary_low"}).context["page_obj"]
        self.assertEqual(page[0].salary_min, 30000)
        self.assertEqual(self.client.get(url, {"page": "invalid"}).status_code, 200)

    def test_profile_photo_and_company_logo_upload(self):
        output = BytesIO()
        Image.new("RGB", (10, 10), "purple").save(output, "PNG")
        self.client.force_login(self.seeker)
        response = self.client.post(reverse("accounts:profile"), {"first_name": "Amelia", "last_name": "Khan", "email": self.seeker.email, "photo": SimpleUploadedFile("avatar.png", output.getvalue(), "image/png"), "skills": "Python"})
        self.assertEqual(response.status_code, 302)
        self.assertContains(self.client.get(reverse("accounts:profile")), "Your profile photo")
        self.client.force_login(self.employer)
        response = self.client.post(reverse("accounts:company"), {"name": "NovaTech", "description": "Thoughtful software.", "location": "Austin", "logo": SimpleUploadedFile("logo.png", output.getvalue(), "image/png")})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(self.job.get_absolute_url()).status_code, 200)

    def test_password_reset_and_change(self):
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            self.client.post(reverse("accounts:password_reset"), {"email": self.seeker.email})
            self.assertEqual(len(mail.outbox), 1)
            self.assertIn("/accounts/password/reset/", mail.outbox[0].body)
        self.client.force_login(self.seeker)
        response = self.client.post(reverse("accounts:password_change"), {"old_password": "StrongPass123!", "new_password1": "DifferentPass456!", "new_password2": "DifferentPass456!"})
        self.assertEqual(response.status_code, 302)
        self.seeker.refresh_from_db()
        self.assertTrue(self.seeker.check_password("DifferentPass456!"))

    def test_csrf_protection(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.seeker)
        self.assertEqual(client.post(reverse("jobs:toggle_save", args=[self.job.pk])).status_code, 403)

    def test_admin_public_pages_and_resource_tables(self):
        for name in ["core:home", "core:companies", "core:categories", "jobs:list", "accounts:login", "accounts:register", "accounts:password_reset"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard:admin")).status_code, 200)
        for resource in ["users", "companies", "jobs", "applications", "categories", "saved-jobs"]:
            self.assertEqual(self.client.get(reverse("dashboard:admin_manage", args=[resource])).status_code, 200)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class SeedTests(TestCase):
    def test_seed_is_repeatable_and_preserves_existing_passwords(self):
        with TemporaryDirectory(dir=settings.BASE_DIR, prefix=".test-media-") as media, override_settings(MEDIA_ROOT=media, DEBUG=True):
            call_command("seed_data", stdout=StringIO())
            user = User.objects.get(username="jobseeker")
            user.set_password("ChangedPassword456!")
            user.save()
            call_command("seed_data", stdout=StringIO())
            self.assertEqual(User.objects.count(), 14)
            self.assertEqual(Company.objects.count(), 5)
            self.assertEqual(Category.objects.count(), 12)
            self.assertEqual(Job.objects.count(), 26)
            self.assertEqual(Application.objects.count(), 18)
            self.assertEqual(SavedJob.objects.count(), 16)
            user.refresh_from_db()
            self.assertTrue(user.check_password("ChangedPassword456!"))
