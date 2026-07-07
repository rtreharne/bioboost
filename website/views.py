from django.http import Http404
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse

from standalone.models import Course, CourseConfig
from standalone.services.demo_mode import ensure_demo_access


OCR_PHYSICS_COURSE_SLUG = "a-level-physics-ocr"
LANDING_FEATURES = (
    "Infinite A-Level physics practice",
    "Immediate feedback and support",
    "Step-by-step help when you get stuck",
    "Ask about anything in the course",
    "Build confidence one question at a time",
)


def home(request: HttpRequest) -> HttpResponse:
    course = Course.objects.filter(slug=OCR_PHYSICS_COURSE_SLUG, is_active=True).select_related("config").first()
    if course is None:
        raise Http404("OCR Physics demo course is not available.")

    config, _created = CourseConfig.objects.get_or_create(course=course)
    if not config.demo_enabled:
        config.demo_enabled = True
        config.save(update_fields=["demo_enabled", "updated_at"])

    access = ensure_demo_access(course)
    redirect_delay_ms = 15000
    context = {
        "cta_url": reverse("standalone:demo_practice", args=[access.token]),
        "redirect_delay_ms": redirect_delay_ms,
        "redirect_delay_seconds": redirect_delay_ms // 1000,
        "landing_features": LANDING_FEATURES,
    }
    return render(request, "website/home.html", context)
