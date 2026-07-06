import importlib.util
import os
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse


class RootHomepageTests(TestCase):
    def test_root_renders_homepage_with_sign_in_cta_for_unauthenticated_users(self):
        response = self.client.get(reverse("website:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "website/home.html")
        self.assertContains(response, "NINE POINT EIGHT ONE")
        self.assertContains(response, "Unlimited A-Level Physics Practice Questions")
        self.assertContains(response, 'data-home-cta', html=False)
        self.assertContains(response, f'href="{reverse("standalone:login")}"', html=False)
        self.assertContains(response, "Sign in")

    def test_root_renders_homepage_with_dashboard_cta_for_authenticated_users(self):
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
        self.assertContains(response, f'href="{reverse("standalone:dashboard")}"', html=False)
        self.assertContains(response, "Open dashboard")


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

        with patch.dict(os.environ, {"MEDIA_ROOT": "/tmp/ninepointeightone-media-test"}, clear=False):
            spec.loader.exec_module(module)

        self.assertEqual(module.MEDIA_ROOT, "/tmp/ninepointeightone-media-test")
