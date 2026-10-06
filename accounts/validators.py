"""Small, explicit upload validators shared by profiles and applications."""
from pathlib import Path
from uuid import uuid4

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


def resume_path(instance, filename):
    return f"resumes/{uuid4().hex}{Path(filename).suffix.lower()}"


def photo_path(instance, filename):
    return f"photos/{uuid4().hex}{Path(filename).suffix.lower()}"


def logo_path(instance, filename):
    return f"logos/{uuid4().hex}{Path(filename).suffix.lower()}"


def validate_resume(value):
    if value.size > 5 * 1024 * 1024:
        raise ValidationError("Your resume must be 5 MB or smaller.")
    if Path(value.name).suffix.lower() != ".pdf":
        raise ValidationError("Please upload a PDF resume.")
    value.open("rb")
    signature = value.read(5)
    value.seek(0)
    if signature != b"%PDF-":
        raise ValidationError("The uploaded file is not a valid PDF.")


def validate_image(value):
    if value.size > 2 * 1024 * 1024:
        raise ValidationError("Images must be 2 MB or smaller.")
    if Path(value.name).suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise ValidationError("Use a JPG, PNG or WebP image.")
    try:
        value.open("rb")
        with Image.open(value) as image:
            if image.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValidationError("Use a JPG, PNG or WebP image.")
            image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValidationError("Please upload a valid image.") from exc
    finally:
        value.seek(0)
