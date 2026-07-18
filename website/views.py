from django.http import Http404
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse

from standalone.models import Course, CourseConfig
from standalone.services.demo_mode import ensure_demo_access


BIOBOOST_FOUNDATIONS_COURSE_SLUG = "bioboost-foundations"
HOME_REDIRECT_DELAY_MS = 15000


def home(request: HttpRequest) -> HttpResponse:
    course = Course.objects.filter(slug=BIOBOOST_FOUNDATIONS_COURSE_SLUG, is_active=True).select_related("config").first()
    if course is None:
        raise Http404("BioBoost Foundations demo course is not available.")

    config, _created = CourseConfig.objects.get_or_create(course=course)
    if not config.demo_enabled:
        config.demo_enabled = True
        config.save(update_fields=["demo_enabled", "updated_at"])

    access = ensure_demo_access(course)
    context = {
        "course": course,
        "cta_url": reverse("standalone:demo_practice", args=[access.token]),
        "redirect_delay_ms": HOME_REDIRECT_DELAY_MS,
    }
    return render(request, "website/home.html", context)
