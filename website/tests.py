import importlib.util
import os
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from standalone.models import Course, CourseConfig, CourseDemoAccess
from website.views import BIOBOOST_FOUNDATIONS_COURSE_SLUG


class RootHomepageTests(TestCase):
    def create_foundations_demo_course(self, *, demo_enabled=False):
        teacher = get_user_model().objects.create_user(
            username="foundationsteacher",
            email="foundationsteacher@example.com",
            password="password123",
            role="teacher",
        )
        course = Course.objects.create(
            teacher=teacher,
            title="BioBoost: Foundations",
            slug=BIOBOOST_FOUNDATIONS_COURSE_SLUG,
            summary="BioBoost Foundations demo course.",
        )
        CourseConfig.objects.create(course=course, demo_enabled=demo_enabled)
        access = CourseDemoAccess.objects.create(course=course)
        return course, access

    def test_root_renders_demo_landing_for_unauthenticated_users(self):
        _course, access = self.create_foundations_demo_course()

        response = self.client.get(reverse("website:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "website/home.html")
        self.assertContains(response, "BioBoost")
        self.assertContains(response, "AI Skills for Bioscientists")
        self.assertContains(response, "Demo course: BioBoost: Foundations")
        self.assertContains(response, "Opening BioBoost: Foundations demo", html=False)
        self.assertContains(response, "Preparing the full-screen chat demo workspace.")
        self.assertContains(response, "Powered by")
        self.assertContains(response, "https://libguides.liverpool.ac.uk/knowhow", html=False)
        self.assertContains(response, "website/img/knowhow_pink_square.png", html=False)
        self.assertContains(response, 'data-home-loader', html=False)
        self.assertContains(response, f'data-redirect-url="{reverse("standalone:demo_practice", args=[access.token])}"', html=False)
        self.assertContains(response, 'data-delay-ms="15000"', html=False)
        self.assertNotContains(response, ">15s<", html=False)
        self.assertNotContains(response, "Enter demo now")
        self.assertNotContains(response, 'data-home-cta', html=False)
        self.assertNotContains(response, "Sign in")
        self.assertNotContains(response, "Open dashboard")

    def test_root_renders_same_demo_landing_for_authenticated_users(self):
        _course, access = self.create_foundations_demo_course()
        user = get_user_model().objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="password123",
            role="teacher",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("website:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "website/home.html")
        self.assertContains(response, "BioBoost")
        self.assertContains(response, "Opening BioBoost: Foundations demo", html=False)
        self.assertContains(response, f'data-redirect-url="{reverse("standalone:demo_practice", args=[access.token])}"', html=False)
        self.assertContains(response, 'data-delay-ms="15000"', html=False)
        self.assertNotContains(response, 'data-home-cta', html=False)
        self.assertNotContains(response, "Open dashboard")
        self.assertNotContains(response, "Sign in")

    def test_root_enables_demo_mode_for_existing_foundations_course(self):
        course, access = self.create_foundations_demo_course(demo_enabled=False)

        response = self.client.get(reverse("website:home"))

        self.assertEqual(response.status_code, 200)
        course.config.refresh_from_db()
        self.assertTrue(course.config.demo_enabled)
        self.assertContains(response, f'data-redirect-url="{reverse("standalone:demo_practice", args=[access.token])}"', html=False)

    def test_root_returns_404_when_foundations_course_is_missing(self):
        response = self.client.get(reverse("website:home"))

        self.assertEqual(response.status_code, 404)


class AdminBootstrapCommandTests(TestCase):
    @patch.dict(
        os.environ,
        {
            "DJANGO_ADMIN_USERNAME": "renderadmin",
            "DJANGO_ADMIN_PASSWORD": "super-secret-pass",
        },
        clear=False,
    )
    def test_ensure_admin_user_creates_superuser(self):
        call_command("ensure_admin_user")

        user = get_user_model().objects.get(username="renderadmin")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password("super-secret-pass"))

    @patch.dict(
        os.environ,
        {
            "DJANGO_ADMIN_USERNAME": "renderadmin",
            "DJANGO_ADMIN_PASSWORD": "new-secret-pass",
        },
        clear=False,
    )
    def test_ensure_admin_user_updates_existing_superuser_password(self):
        user = get_user_model().objects.create_superuser(
            username="renderadmin",
            email="old@example.com",
            password="old-pass",
        )

        call_command("ensure_admin_user")

        user.refresh_from_db()
        self.assertTrue(user.check_password("new-secret-pass"))


class SettingsConfigurationTests(TestCase):
    def test_media_root_can_be_configured_with_environment_variable(self):
        settings_path = Path(__file__).resolve().parent.parent / "config" / "settings.py"
        spec = importlib.util.spec_from_file_location("config_settings_media_root_test", settings_path)
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)

        with patch.dict(os.environ, {"MEDIA_ROOT": "/tmp/bioboost-media-test"}, clear=False):
            spec.loader.exec_module(module)

        self.assertEqual(module.MEDIA_ROOT, "/tmp/bioboost-media-test")
