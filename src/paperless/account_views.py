from allauth.account.views import SignupView
from allauth.headless.account.views import LoginView as HeadlessLoginView
from allauth.headless.account.views import SignupView as HeadlessSignupView
from allauth.headless.base.response import ForbiddenResponse
from allauth.headless.constants import Client
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from paperless.global_totp import get_global_totp_code
from paperless.global_totp import verify_global_totp
from paperless.hcaptcha import verify_hcaptcha


class HCaptchaSignupView(SignupView):
    def form_valid(self, form):
        if settings.HCAPTCHA_ENABLED:
            token = self.request.POST.get("h-captcha-response", "")
            if not token:
                form.add_error(None, _("Please complete the hCaptcha challenge."))
                return self.form_invalid(form)
            if not verify_hcaptcha(self.request, token):
                form.add_error(
                    None,
                    _("hCaptcha verification failed. Please try again."),
                )
                return self.form_invalid(form)

        return super().form_valid(form)


class GlobalTotpHeadlessSignupView(HeadlessSignupView):
    """Protect app signup with TOTP and browser signup with hCaptcha."""

    def post(self, request, *args, **kwargs):
        if self.client == Client.APP and settings.GLOBAL_TOTP_ENABLED:
            code = get_global_totp_code(request, self.data)
            if not verify_global_totp(code):
                return ForbiddenResponse(request)
        elif self.client == Client.BROWSER and settings.HCAPTCHA_ENABLED:
            token = request.headers.get("X-HCaptcha-Response", "")
            token = token or self.data.get("h-captcha-response", "")
            if not token or not verify_hcaptcha(request, token):
                return ForbiddenResponse(request)
        return super().post(request, *args, **kwargs)


class GlobalTotpHeadlessLoginView(HeadlessLoginView):
    """Require the global TOTP before validating app login credentials."""

    def handle_input(self, data):
        if settings.GLOBAL_TOTP_ENABLED:
            code = get_global_totp_code(self.request, data)
            if not verify_global_totp(code):
                return ForbiddenResponse(self.request)
        return super().handle_input(data)
