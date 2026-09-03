import logging

import httpx
from django.conf import settings
from django.http import HttpRequest
from python_ipware import IpWare

logger = logging.getLogger("paperless.auth")

HCAPTCHA_VERIFY_URL = "https://api.hcaptcha.com/siteverify"


def verify_hcaptcha(request: HttpRequest, token: str) -> bool:
    payload = {
        "secret": settings.HCAPTCHA_SECRET_KEY,
        "response": token,
        "sitekey": settings.HCAPTCHA_SITE_KEY,
    }

    ipware = IpWare(proxy_list=settings.TRUSTED_PROXIES)
    client_ip, _ = ipware.get_client_ip(meta=request.META)
    if client_ip is not None:
        payload["remoteip"] = str(client_ip)

    try:
        response = httpx.post(
            HCAPTCHA_VERIFY_URL,
            data=payload,
            timeout=settings.HCAPTCHA_TIMEOUT,
        )
        response.raise_for_status()
        result = response.json()
    except (httpx.HTTPError, ValueError):
        logger.warning("Unable to verify hCaptcha response", exc_info=True)
        return False

    if not result.get("success", False):
        error_codes = result.get("error-codes", [])
        logger.info("hCaptcha rejected login: %s", ", ".join(error_codes))
        return False

    return True
