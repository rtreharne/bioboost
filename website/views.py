from datetime import datetime

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse


def home(request: HttpRequest) -> HttpResponse:
    is_authenticated = request.user.is_authenticated
    context = {
        "year": datetime.now().year,
        "cta_url": reverse("standalone:dashboard") if is_authenticated else reverse("standalone:login"),
        "cta_label": "Open dashboard" if is_authenticated else "Sign in",
    }
    return render(request, "website/home.html", context)
