import base64
import binascii
import hashlib
import hmac
import struct
import time
from collections.abc import Mapping
from typing import Any

from django.conf import settings
from django.http import HttpRequest

GLOBAL_TOTP_HEADER = "X-Paperless-OTP"
GLOBAL_TOTP_DIGITS = 6
GLOBAL_TOTP_PERIOD = 30


def get_global_totp_code(
    request: HttpRequest,
    data: Mapping[str, Any] | None = None,
) -> str:
    """Read a global TOTP from the preferred header or an ``otp`` form field."""
    header_code = request.headers.get(GLOBAL_TOTP_HEADER, "")
    if header_code:
        return header_code.strip()

    if data is not None:
        return str(data.get("otp", "")).strip()

    return str(request.POST.get("otp", "")).strip()


def verify_global_totp(code: str, at_time: float | None = None) -> bool:
    """Verify a six-digit RFC 6238 TOTP using the configured global secret."""
    if len(code) != GLOBAL_TOTP_DIGITS or not code.isascii() or not code.isdigit():
        return False

    secret = settings.GLOBAL_TOTP_SECRET.replace(" ", "").upper()
    padding = "=" * (-len(secret) % 8)
    try:
        key = base64.b32decode(secret + padding, casefold=True)
    except (binascii.Error, ValueError):
        return False

    if not key:
        return False

    timestamp = time.time() if at_time is None else at_time
    counter = int(timestamp // GLOBAL_TOTP_PERIOD)
    window = settings.GLOBAL_TOTP_WINDOW

    for offset in range(-window, window + 1):
        candidate_counter = counter + offset
        if candidate_counter < 0:
            continue
        digest = hmac.new(
            key,
            struct.pack(">Q", candidate_counter),
            hashlib.sha1,
        ).digest()
        position = digest[-1] & 0x0F
        value = struct.unpack(">I", digest[position : position + 4])[0]
        value &= 0x7FFFFFFF
        candidate = str(value % (10**GLOBAL_TOTP_DIGITS)).zfill(GLOBAL_TOTP_DIGITS)
        if hmac.compare_digest(candidate, code):
            return True

    return False
