from allauth.account.views import SignupView
from django.conf import settings
from django.utils.translation import gettext_lazy as _

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
