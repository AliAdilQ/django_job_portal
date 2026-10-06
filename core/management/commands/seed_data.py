"""Create an idempotent local demo without resetting existing passwords or edits."""
from datetime import timedelta
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from PIL import Image, ImageDraw, ImageFont

from accounts.models import Company, Profile, User
from applications.models import Application
from core.demo import resume_pdf
from jobs.models import Category, Job, SavedJob

CATEGORIES = [
    ("Software Development", "code"), ("Web Development", "code"), ("Data Science", "chart"),
    ("Machine Learning", "layers"), ("Artificial Intelligence", "sparkle"), ("Cybersecurity", "shield"),
    ("UI/UX Design", "palette"), ("Marketing", "send"), ("Finance", "chart"),
    ("Human Resources", "users"), ("Customer Support", "chat"), ("Project Management", "briefcase"),
]
COMPANIES = [
    ("NovaTech Solutions", "Austin, TX", "Software & Technology", "50–200 people", "We build software that makes everyday work feel effortless. Our distributed team values thoughtful engineering, honest collaboration, and the space to do your best work. From developer tools to customer platforms, we turn complex problems into useful products."),
    ("PixelForge Studio", "New York, NY", "Design & Digital Products", "20–50 people", "An independent design studio crafting memorable digital experiences. We bring strategy, design, and engineering together to help ambitious brands connect with their communities. Curiosity, care, and a sharp eye for detail drive everything we make."),
    ("DataSphere Labs", "San Francisco, CA", "Data & Research", "50–200 people", "We help organizations turn data into confident decisions. Our researchers and engineers work on practical machine learning, transparent analytics, and responsible AI. We invest in open knowledge, mentorship, and meaningful problems."),
    ("CloudNova Technologies", "Seattle, WA", "Cloud Infrastructure", "200–500 people", "CloudNova makes resilient infrastructure accessible to teams of every size. We build secure cloud platforms, automation tools, and observability systems. Join people who love solving hard problems while keeping things simple for our customers."),
    ("BrightPath Digital", "Boston, MA", "Digital Services", "50–200 people", "We partner with growing businesses to build a brighter digital future. Our multidisciplinary team combines product strategy, marketing, customer care, and technology. We believe a supportive workplace and meaningful client relationships create our best work."),
]
# title, company index, category index, skills, minimum salary, experience
POSITIONS = [
    ("Python Developer", 0, 0, "Python, Django, Git, Testing", 85000, "mid"),
    ("Django Developer", 0, 1, "Django, Python, REST APIs, HTML", 90000, "mid"),
    ("Frontend Developer", 1, 1, "JavaScript, React, CSS, Accessibility", 80000, "junior"),
    ("Backend Developer", 0, 0, "Python, SQL, APIs, System design", 95000, "senior"),
    ("Machine Learning Engineer", 2, 3, "Python, PyTorch, MLOps, Statistics", 125000, "senior"),
    ("Data Analyst", 2, 2, "SQL, Python, Dashboards, Analytics", 75000, "junior"),
    ("Data Scientist", 2, 2, "Python, Statistics, Experimentation, SQL", 110000, "mid"),
    ("NLP Engineer", 2, 4, "Python, NLP, Transformers, Evaluation", 120000, "senior"),
    ("DevOps Engineer", 3, 0, "Docker, Linux, CI/CD, Cloud", 105000, "mid"),
    ("UI/UX Designer", 1, 6, "Figma, User research, Prototyping, Design systems", 90000, "mid"),
    ("Product Designer", 1, 6, "Figma, Interaction design, Research", 100000, "senior"),
    ("Security Engineer", 3, 5, "Security reviews, Python, Networking, Threat modeling", 115000, "senior"),
    ("Digital Marketing Specialist", 4, 7, "SEO, Analytics, Content strategy, Campaigns", 65000, "junior"),
    ("Financial Analyst", 4, 8, "Financial modeling, Excel, Forecasting, Reporting", 70000, "mid"),
    ("People Operations Partner", 4, 9, "Recruiting, Onboarding, Communication", 78000, "mid"),
    ("Customer Success Associate", 4, 10, "Customer care, Communication, CRM", 52000, "entry"),
    ("Technical Project Manager", 3, 11, "Agile, Planning, Communication, Delivery", 108000, "lead"),
    ("Software Engineering Intern", 0, 0, "Python, Git, Problem solving", 35000, "entry"),
    ("Junior Web Developer", 1, 1, "HTML, CSS, JavaScript, Git", 60000, "junior"),
    ("AI Research Engineer", 2, 4, "Python, Machine learning, Research, Evaluation", 135000, "senior"),
    ("Cloud Platform Engineer", 3, 0, "Kubernetes, Linux, Python, Observability", 118000, "mid"),
    ("Content Marketing Manager", 4, 7, "Storytelling, Content strategy, SEO", 85000, "lead"),
    ("Freelance Brand Designer", 1, 6, "Brand design, Illustration, Typography", 70000, "mid"),
    ("Data Engineering Specialist", 2, 2, "Python, SQL, Data pipelines, Testing", 105000, "mid"),
    ("Remote Support Specialist", 4, 10, "Troubleshooting, Communication, Documentation", 55000, "junior"),
    ("Part-Time Talent Coordinator", 4, 9, "Scheduling, Recruiting, Communication", 40000, "entry"),
]


def initials_image(text, index):
    colors = [("#efebff", "#7056dd"), ("#e5f5ed", "#3c9a72"), ("#eaf3ff", "#5480bb"), ("#fff0e3", "#bd874e"), ("#fbeaf2", "#aa6690")]
    background, foreground = colors[index % len(colors)]
    image = Image.new("RGB", (180, 180), background)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(settings.BASE_DIR / "static/vendor/DM-Sans.ttf"), 65)
    draw.text((90, 88), text, font=font, fill=foreground, anchor="mm")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


class Command(BaseCommand):
    help = "Populate local SQLite with fictional accounts, jobs, applications and resumes. Safe to repeat."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo accounts are only available with DEBUG=True. Never seed a production deployment.")
        with transaction.atomic():
            self.seed()
        self.stdout.write(self.style.SUCCESS("Demo ready: 1 admin, 5 employers, 8 seekers, 5 companies, 12 categories, 26 jobs, 18 applications and 16 bookmarks. Existing records and passwords were preserved."))

    def create_user(self, username, email, password, first_name, last_name, role="seeker", admin=False):
        user, created = User.objects.get_or_create(username=username, defaults={"email": email, "first_name": first_name, "last_name": last_name, "role": role, "is_staff": admin, "is_superuser": admin})
        if created:
            user.set_password(password)
            user.save()
        elif user.email != email or user.role != role or user.is_superuser != admin:
            raise CommandError(f"Seed username '{username}' is already used by another account. No database changes were made.")
        return user

    def seed(self):
        self.create_user("admin", "admin@example.com", "Admin12345!", "Alex", "Morgan", admin=True)
        categories = [Category.objects.get_or_create(slug=slugify(name), defaults={"name": name, "icon": icon})[0] for name, icon in CATEGORIES]
        companies = []
        employer_names = [("Olivia", "Bennett"), ("Ethan", "Park"), ("Sophia", "Chen"), ("Noah", "Williams"), ("Isabella", "Reed")]
        for index, ((name, location, industry, size, description), (first, last)) in enumerate(zip(COMPANIES, employer_names)):
            user = self.create_user("employer" if index == 0 else f"employer{index+1}", "employer@example.com" if index == 0 else f"employer{index+1}@example.com", "Employer123!", first, last, "employer")
            Profile.objects.get_or_create(user=user, defaults={"headline": f"Talent partner at {name}", "location": location})
            company, created = Company.objects.get_or_create(owner=user, defaults={"name": name, "location": location, "industry": industry, "size": size, "description": description, "website": "https://example.com"})
            if created:
                company.logo.save("logo.png", ContentFile(initials_image(name[0], index)))
            companies.append(company)
        names = [("Amelia", "Khan"), ("James", "Miller"), ("Sofia", "Rivera"), ("Liam", "Patel"), ("Emma", "Wilson"), ("Oliver", "Scott"), ("Mia", "Taylor"), ("Lucas", "Garcia")]
        seekers = []
        for index, (first, last) in enumerate(names):
            user = self.create_user("jobseeker" if index == 0 else f"jobseeker{index+1}", "jobseeker@example.com" if index == 0 else f"jobseeker{index+1}@example.com", "JobSeeker123!", first, last)
            profile, created = Profile.objects.get_or_create(user=user, defaults={
                "headline": ["Python developer & curious problem solver", "Product designer", "Data analyst", "Frontend developer"][index % 4],
                "skills": "Python, Django, JavaScript, SQL, Git, Collaboration", "location": ["Austin, TX", "New York, NY", "San Francisco, CA"][index % 3],
                "bio": "I enjoy turning challenging ideas into thoughtful, useful digital experiences. I'm looking for a collaborative team where I can keep learning, contribute meaningfully, and help build something people love.",
                "education": "BSc in Computer Science · Riverside University\nGraduated with distinction; focused on software engineering and applied statistics.",
                "experience": "Software Developer · Horizon Digital · 2023–2026\nBuilt accessible customer tools, improved API reliability, and collaborated with designers to ship practical product improvements.",
            })
            if created:
                profile.photo.save("photo.png", ContentFile(initials_image(first[0]+last[0], index)), save=False)
                profile.resume.save("resume.pdf", ContentFile(resume_pdf(user.display_name, profile.headline)), save=False)
                profile.save()
            seekers.append(user)
        jobs = []
        for index, (title, company_index, category_index, skills, salary, level) in enumerate(POSITIONS):
            company = companies[company_index]
            job_type = "internship" if "Intern" in title else "freelance" if "Freelance" in title else "part_time" if "Part-Time" in title else "remote" if "Remote" in title else "contract" if index == 23 else "full_time"
            job, created = Job.objects.get_or_create(title=title, company=company, defaults={
                "category": categories[category_index], "skills": skills, "location": company.location,
                "salary_min": salary, "salary_max": salary+25000, "experience_level": level, "job_type": job_type,
                "remote": index % 3 == 0 or job_type in {"remote", "freelance"}, "deadline": timezone.localdate()+timedelta(days=45+index),
                "vacancies": 2 if index % 4 == 0 else 1, "featured": index in {0, 4, 9},
                "education": "A relevant degree or equivalent practical experience. We value curiosity and demonstrated skills.",
                "description": f"Join {company.name} as a {title} and help us build work that makes a difference. You'll collaborate with a thoughtful, multidisciplinary team, bring fresh ideas to real challenges, and have room to grow your craft.\n\nWe offer flexible working arrangements, a learning budget, transparent feedback, and a supportive environment. We care about the quality of your thinking and the positive impact you bring to the people around you.",
                "responsibilities": "Own meaningful projects from the first conversation to the final delivery.\nCollaborate with teammates to understand user needs and turn ideas into practical solutions.\nCommunicate progress clearly, review work thoughtfully, and share what you learn.\nHelp improve our tools, processes, and the experience we create for customers.",
                "requirements": f"Practical experience with {skills.lower()}.\nClear communication and a collaborative approach to problem solving.\nA portfolio or examples that show how you approach your work.\nThe curiosity to learn, ask good questions, and support the people around you.",
            })
            if created:
                Job.objects.filter(pk=job.pk).update(created_at=timezone.now()-timedelta(days=index // 3))
            jobs.append(job)
        statuses = ["pending", "review", "shortlisted", "interview", "rejected", "hired"]
        for index in range(18):
            seeker = seekers[index % 8]
            job = jobs[index % 13]
            application, created = Application.objects.get_or_create(applicant=seeker, job=job, defaults={"cover_letter": f"Hello {job.company.name} team,\n\nI'm excited to apply for the {job.title} position. Your commitment to thoughtful work and collaboration resonates with me. I would bring hands-on experience, a curious approach to solving problems, and a genuine interest in your team's mission.\n\nI'd love the chance to share more about my work and learn how I could contribute. Thank you for considering my application.\n\nBest,\n{seeker.display_name}", "status": statuses[index % 6]})
            if created:
                application.resume.save("resume.pdf", ContentFile(resume_pdf(seeker.display_name, seeker.profile.headline)), save=False)
                application.save()
                Application.objects.filter(pk=application.pk).update(created_at=timezone.now()-timedelta(days=index % 7))
        for index, seeker in enumerate(seekers):
            for offset in [14, 18]:
                SavedJob.objects.get_or_create(user=seeker, job=jobs[(index+offset) % len(jobs)])
