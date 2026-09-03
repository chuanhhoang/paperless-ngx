import base64
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
        GLOBAL_TOTP_ENABLED=True,
        GLOBAL_TOTP_SECRET="JBSWY3DPEHPK3PXP",
        HCAPTCHA_ENABLED=True,
        HCAPTCHA_SITE_KEY="test-site-key",
    )
    def test_browser_signup_keeps_hcaptcha_when_global_totp_is_enabled(self):
        response = self.client.get(reverse("account_signup"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'class="h-captcha')
        self.assertNotContains(response, 'name="otp"')

    @override_settings(
        ACCOUNT_ALLOW_SIGNUPS=True,
        GLOBAL_TOTP_ENABLED=True,
        GLOBAL_TOTP_SECRET="JBSWY3DPEHPK3PXP",
    )
    def test_headless_app_signup_requires_global_totp(self):
        response = self.client.post(
            "/api/auth/headless/app/v1/auth/signup",
            data={
                "username": f"signup-{uuid.uuid4().hex}",
                "email": "",
                "password": "a-secure-test-password-123",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(
        ACCOUNT_ALLOW_SIGNUPS=True,
        ACCOUNT_EMAIL_VERIFICATION="none",
        GLOBAL_TOTP_ENABLED=True,
        GLOBAL_TOTP_SECRET="JBSWY3DPEHPK3PXP",
    )
    @patch("paperless.account_views.verify_global_totp", return_value=True)
    def test_headless_app_signup_accepts_global_totp_field(self, verify_mock):
        username = f"signup-{uuid.uuid4().hex}"

        response = self.client.post(
            "/api/auth/headless/app/v1/auth/signup",
            data={
                "username": username,
                "email": "",
                "password": "a-secure-test-password-123",
                "otp": "123456",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(User.objects.filter(username=username).exists())
        verify_mock.assert_called_once_with("123456")

    @override_settings(
        GLOBAL_TOTP_ENABLED=True,
        GLOBAL_TOTP_SECRET="JBSWY3DPEHPK3PXP",
    )
    def test_api_token_authentication_requires_global_totp(self):
        user = User.objects.create_user(username="app-user", password="password")

        response = self.client.post(
            "/api/token/",
            data={"username": user.username, "password": "password"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["non_field_errors"],
            ["Invalid global one-time password"],
        )

    @override_settings(
        GLOBAL_TOTP_ENABLED=True,
        GLOBAL_TOTP_SECRET="JBSWY3DPEHPK3PXP",
    )
    @patch("paperless.serialisers.verify_global_totp", return_value=True)
    def test_api_token_authentication_accepts_global_totp_header(self, verify_mock):
        user = User.objects.create_user(username="app-user", password="password")

        response = self.client.post(
            "/api/token/",
            data={"username": user.username, "password": "password"},
            headers={"X-Paperless-OTP": "123456"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.json())
        verify_mock.assert_called_once_with("123456")

    @override_settings(
        GLOBAL_TOTP_ENABLED=True,
        GLOBAL_TOTP_SECRET="JBSWY3DPEHPK3PXP",
    )
    def test_headless_app_login_requires_global_totp(self):
        user = User.objects.create_user(username="app-user", password="password")

        response = self.client.post(
            "/api/auth/headless/app/v1/auth/login",
            data={"username": user.username, "password": "password"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(
        GLOBAL_TOTP_ENABLED=True,
        GLOBAL_TOTP_SECRET="JBSWY3DPEHPK3PXP",
    )
    @patch("paperless.account_views.verify_global_totp", return_value=True)
    def test_headless_app_login_accepts_global_totp_field(self, verify_mock):
        user = User.objects.create_user(username="app-user", password="password")

        response = self.client.post(
            "/api/auth/headless/app/v1/auth/login",
            data={
                "username": user.username,
                "password": "password",
                "otp": "123456",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["meta"]["is_authenticated"])
        verify_mock.assert_called_once_with("123456")

    @override_settings(
        GLOBAL_TOTP_ENABLED=True,
        GLOBAL_TOTP_SECRET="JBSWY3DPEHPK3PXP",
    )
    def test_global_totp_disables_basic_authentication(self):
        user = User.objects.create_user(username="app-user", password="password")
        credentials = base64.b64encode(f"{user.username}:password".encode()).decode()

        response = self.client.get(
            "/api/profile/",
            headers={"Authorization": f"Basic {credentials}"},
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.json()["detail"],
            "Basic authentication is disabled when global TOTP is enabled",
        )

    @override_settings(
        ACCOUNT_ALLOW_SIGNUPS=True,
        GLOBAL_TOTP_ENABLED=True,
        GLOBAL_TOTP_SECRET="JBSWY3DPEHPK3PXP",
        HCAPTCHA_ENABLED=True,
        HCAPTCHA_SITE_KEY="test-site-key",
    )
    def test_headless_browser_signup_still_requires_hcaptcha(self):
        response = self.client.post(
            "/api/auth/headless/browser/v1/auth/signup",
            data={
                "username": f"signup-{uuid.uuid4().hex}",
                "email": "",
                "password": "a-secure-test-password-123",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(
        ACCOUNT_ALLOW_SIGNUPS=True,
        ACCOUNT_EMAIL_VERIFICATION="none",
        GLOBAL_TOTP_ENABLED=True,
        GLOBAL_TOTP_SECRET="JBSWY3DPEHPK3PXP",
        HCAPTCHA_ENABLED=True,
        HCAPTCHA_SITE_KEY="test-site-key",
    )
    @patch("paperless.account_views.verify_hcaptcha", return_value=True)
    def test_headless_browser_signup_accepts_hcaptcha(self, verify_mock):
        username = f"signup-{uuid.uuid4().hex}"

        response = self.client.post(
            "/api/auth/headless/browser/v1/auth/signup",
            data={
                "username": username,
                "email": "",
                "password": "a-secure-test-password-123",
                "h-captcha-response": "test-response-token",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(User.objects.filter(username=username).exists())
        verify_mock.assert_called_once()

    @override_settings(
        ACCOUNT_ALLOW_SIGNUPS=True,
        ACCOUNT_SIGNUP_EMAIL_REQUIRED=True,
        ACCOUNT_SIGNUP_FIELDS=["email*", "username*", "password1*", "password2*"],
        HCAPTCHA_ENABLED=True,
        HCAPTCHA_SITE_KEY="test-site-key",
    )
    @patch("paperless.account_views.verify_hcaptcha")
    def test_signup_requires_email_before_hcaptcha(self, verify_mock):
        username = f"signup-{uuid.uuid4().hex}"

        page = self.client.get(reverse("account_signup"))
        self.assertContains(page, 'name="email"')
        self.assertContains(page, "required")
        self.assertNotContains(page, "Email (optional)")

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
        self.assertContains(response, "This field is required")
        self.assertFalse(User.objects.filter(username=username).exists())
        verify_mock.assert_not_called()

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
        ACCOUNT_DEFAULT_GROUPS=["Uploader"],
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
        self.assertTrue(
            User.objects.get(username=username).groups.filter(name="Uploader").exists(),
        )
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
