import uuid
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.test import override_settings
from django.urls import resolve
from django.urls import reverse
from rest_framework import status


class TestApiAuthViews(TestCase):
    def test_api_auth_login_uses_allauth_login_view(self):
        response = self.client.get(reverse("rest_framework:login"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, "account/login.html")

    def test_api_auth_login_uses_same_view_as_account_login(self):
        api_match = resolve("/api/auth/login/")
        account_match = resolve("/accounts/login/")

        self.assertIs(api_match.func.view_class, account_match.func.view_class)

    @override_settings(
        HCAPTCHA_ENABLED=True,
        HCAPTCHA_SITE_KEY="test-site-key",
    )
    def test_login_page_renders_hcaptcha(self):
        response = self.client.get(reverse("account_login"))

        self.assertContains(response, "https://js.hcaptcha.com/1/api.js")
        self.assertContains(response, 'class="h-captcha')
        self.assertContains(response, 'data-sitekey="test-site-key"')

    @override_settings(
        ACCOUNT_ALLOW_SIGNUPS=True,
        HCAPTCHA_ENABLED=True,
        HCAPTCHA_SITE_KEY="test-site-key",
    )
    def test_signup_page_renders_hcaptcha(self):
        response = self.client.get(reverse("account_signup"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, "account/signup.html")
        self.assertContains(response, "https://js.hcaptcha.com/1/api.js")
        self.assertContains(response, 'class="h-captcha')
        self.assertContains(response, 'data-sitekey="test-site-key"')

    @override_settings(
        ACCOUNT_ALLOW_SIGNUPS=True,
        HCAPTCHA_ENABLED=True,
        HCAPTCHA_SITE_KEY="test-site-key",
    )
    def test_signup_requires_hcaptcha(self):
        username = f"signup-{uuid.uuid4().hex}"

        response = self.client.post(
            reverse("account_signup"),
            data={
                "username": username,
                "email": "",
                "password1": "a-secure-test-password-123",
                "password2": "a-secure-test-password-123",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Please complete the hCaptcha challenge")
        self.assertFalse(User.objects.filter(username=username).exists())

    @override_settings(
        ACCOUNT_ALLOW_SIGNUPS=True,
        HCAPTCHA_ENABLED=True,
        HCAPTCHA_SITE_KEY="test-site-key",
    )
    @patch("paperless.account_views.verify_hcaptcha", return_value=False)
    def test_signup_rejects_invalid_hcaptcha(self, verify_mock):
        username = f"signup-{uuid.uuid4().hex}"

        response = self.client.post(
            reverse("account_signup"),
            data={
                "username": username,
                "email": "",
                "password1": "a-secure-test-password-123",
                "password2": "a-secure-test-password-123",
                "h-captcha-response": "invalid-token",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "hCaptcha verification failed")
        self.assertFalse(User.objects.filter(username=username).exists())
        verify_mock.assert_called_once()

    @override_settings(
        ACCOUNT_ALLOW_SIGNUPS=True,
        HCAPTCHA_ENABLED=True,
        HCAPTCHA_SITE_KEY="test-site-key",
        ACCOUNT_EMAIL_VERIFICATION="none",
    )
    @patch("paperless.account_views.verify_hcaptcha", return_value=True)
    def test_signup_accepts_valid_hcaptcha(self, verify_mock):
        username = f"signup-{uuid.uuid4().hex}"

        response = self.client.post(
            reverse("account_signup"),
            data={
                "username": username,
                "email": "",
                "password1": "a-secure-test-password-123",
                "password2": "a-secure-test-password-123",
                "h-captcha-response": "test-response-token",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertTrue(User.objects.filter(username=username).exists())
        verify_mock.assert_called_once()

    @override_settings(DISABLE_REGULAR_LOGIN=True)
    def test_api_auth_login_respects_disable_regular_login(self):
        username = f"testuser-{uuid.uuid4().hex}"
        User.objects.create_user(
            username=username,
            password="testpassword",
        )

        response = self.client.post(
            reverse("rest_framework:login"),
            data={
                "login": username,
                "password": "testpassword",
                "next": "/api/documents/",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, "account/login.html")
        self.assertContains(response, "Regular login is disabled")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_api_auth_logout_uses_named_route(self):
        self.assertEqual(reverse("rest_framework:login"), "/api/auth/login/")
        self.assertEqual(reverse("rest_framework:logout"), "/api/auth/logout/")
