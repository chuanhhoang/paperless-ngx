import base64

from django.test import override_settings

from paperless.global_totp import verify_global_totp

RFC_TEST_SECRET = base64.b32encode(b"12345678901234567890").decode()


@override_settings(GLOBAL_TOTP_SECRET=RFC_TEST_SECRET, GLOBAL_TOTP_WINDOW=0)
def test_verify_global_totp_matches_rfc_6238_vector() -> None:
    # RFC 6238's SHA-1 value at t=59 is 94287082; the six-digit form is 287082.
    assert verify_global_totp("287082", at_time=59)


@override_settings(GLOBAL_TOTP_SECRET=RFC_TEST_SECRET, GLOBAL_TOTP_WINDOW=1)
def test_verify_global_totp_accepts_adjacent_time_step() -> None:
    assert verify_global_totp("287082", at_time=89)


@override_settings(GLOBAL_TOTP_SECRET=RFC_TEST_SECRET, GLOBAL_TOTP_WINDOW=0)
def test_verify_global_totp_rejects_invalid_codes() -> None:
    assert not verify_global_totp("287083", at_time=59)
    assert not verify_global_totp("12345", at_time=59)
    assert not verify_global_totp("12345a", at_time=59)


@override_settings(GLOBAL_TOTP_SECRET="not-base32!", GLOBAL_TOTP_WINDOW=0)
def test_verify_global_totp_rejects_invalid_secret() -> None:
    assert not verify_global_totp("123456", at_time=59)
