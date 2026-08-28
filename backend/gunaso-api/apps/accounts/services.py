"""Business logic for account-level flows that don't belong in views/serializers
per CLAUDE.md section 12:

- **Email verification** for accounts whose address was typed by someone else
  (an org admin creating staff with admin-set credentials).
- **Password reset** ("forgot password") for anyone who can no longer sign in.

Email verification uses stateless, signed tokens (django.core.signing) instead
of a DB-backed model like StaffInvite — verifying twice is harmless
(idempotent), so there is no need to track/invalidate prior tokens the way the
single-use staff invite flow does. Password reset deliberately uses a different
token scheme; see the section header further down for why.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.encoding import DjangoUnicodeDecodeError, force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

User = get_user_model()

EMAIL_VERIFICATION_SALT = 'accounts.email-verification'
EMAIL_VERIFICATION_MAX_AGE_SECONDS = 60 * 60 * 24  # 24h


class EmailVerificationError(Exception):
    """Base class for verification-token failures. Carries a user-safe message."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def generate_email_verification_token(user) -> str:
    return signing.dumps({'user_id': user.id, 'email': user.email}, salt=EMAIL_VERIFICATION_SALT)


def _verification_link(token: str) -> str:
    frontend = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
    return f'{frontend.rstrip("/")}/verify-email/{token}'


def send_verification_email(user, token: str) -> None:
    link = _verification_link(token)
    subject = 'Verify your email on Gunaso'
    message = (
        f'Hi,\n\n'
        f'Please verify your email address to secure your Gunaso account:\n{link}\n\n'
        f'This link expires in 24 hours.\n'
        f'If you did not request this, you can safely ignore this email.\n'
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)


def resolve_email_verification_token(raw_token: str):
    """Returns the User the token was issued for, or raises EmailVerificationError.

    Checks the token's embedded email still matches the user's current email —
    guards against a stale link confirming an address the user has since
    changed again.
    """
    try:
        data = signing.loads(
            raw_token, salt=EMAIL_VERIFICATION_SALT, max_age=EMAIL_VERIFICATION_MAX_AGE_SECONDS,
        )
    except signing.SignatureExpired:
        raise EmailVerificationError('This verification link has expired.')
    except signing.BadSignature:
        raise EmailVerificationError('This verification link is invalid.')

    try:
        user = User.objects.get(pk=data['user_id'])
    except User.DoesNotExist:
        raise EmailVerificationError('This verification link is invalid.')

    if user.email != data['email']:
        raise EmailVerificationError('This verification link is no longer valid — the email has changed.')
    return user


# ──────────────────────────────────────────────────────────────────────────────
# Password reset ("forgot password")
# ──────────────────────────────────────────────────────────────────────────────
# Unlike the email-verification token above, this one is NOT a django.core.signing
# token: it uses django.contrib.auth's default_token_generator, whose hash is
# derived from the user's current password hash and last_login. That buys two
# properties a signed token can't give us — the link stops working the moment
# the password is changed (so a reset link can't be replayed after use), and it
# expires on its own after settings.PASSWORD_RESET_TIMEOUT.

PASSWORD_RESET_SUBJECT = 'Reset your Gunaso password'


class PasswordResetError(Exception):
    """Raised when a reset link's uid/token pair doesn't resolve. Carries a
    user-safe message (never says whether the account exists)."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def generate_password_reset_credentials(user) -> tuple[str, str]:
    """Returns the (uid, token) pair that together identify a reset request."""
    return urlsafe_base64_encode(force_bytes(user.pk)), default_token_generator.make_token(user)


def password_reset_link(uid: str, token: str) -> str:
    """Must match the frontend route in router/index.js exactly —
    `/reset-password/:uid/:token`."""
    frontend = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
    return f'{frontend.rstrip("/")}/reset-password/{uid}/{token}'


def _reset_timeout_hours() -> int:
    return max(1, int(getattr(settings, 'PASSWORD_RESET_TIMEOUT', 259200)) // 3600)


def send_password_reset_email(user, uid: str, token: str) -> None:
    """Sends the reset link as a multipart (plain text + HTML) email.

    Uses EmailMultiAlternatives rather than send_mail so the HTML template in
    templates/email/password_reset.html can be used, while still working
    unchanged against the console backend in dev and django.core.mail.outbox
    in tests.
    """
    context = {
        'user': user,
        'username': user.get_username(),
        'display_name': user.get_full_name() or user.get_username(),
        'reset_link': password_reset_link(uid, token),
        'expiry_hours': _reset_timeout_hours(),
        'site_name': 'Gunaso',
    }
    text_body = render_to_string('email/password_reset.txt', context)
    html_body = render_to_string('email/password_reset.html', context)

    message = EmailMultiAlternatives(
        subject=PASSWORD_RESET_SUBJECT,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    message.attach_alternative(html_body, 'text/html')
    message.send(fail_silently=False)


def request_password_reset(email: str) -> bool:
    """Emails a reset link for `email` if an active account has it.

    Returns whether an email was actually sent — for logging/tests only. The
    view deliberately responds identically either way (no account enumeration,
    CLAUDE.md section 8).
    """
    user = User.objects.filter(email__iexact=(email or '').strip(), is_active=True).first()
    if user is None or not user.has_usable_password():
        # An unusable password means a pending staff invite that was never
        # accepted — that flow has its own single-use link, and issuing a
        # reset token here would let anyone bypass the invite.
        return False

    uid, token = generate_password_reset_credentials(user)
    send_password_reset_email(user, uid, token)
    return True


def resolve_password_reset_token(uid: str, token: str):
    """Returns the User a reset link was issued for, or raises PasswordResetError."""
    invalid = PasswordResetError('This password reset link is invalid or has expired.')
    try:
        user_pk = force_str(urlsafe_base64_decode(uid or ''))
        user = User.objects.get(pk=user_pk, is_active=True)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist, DjangoUnicodeDecodeError):
        raise invalid

    if not default_token_generator.check_token(user, token or ''):
        raise invalid
    return user


def reset_password(user, new_password: str) -> None:
    """Sets the new password and closes every other session for the account.

    Blacklisting outstanding refresh tokens matters here specifically: a
    'forgot password' is the flow someone uses when they suspect their account
    was taken over, so leaving a stolen refresh token alive for up to
    JWT_REFRESH_TOKEN_LIFETIME_DAYS would defeat the point. Mirrors
    apps/platform_admin/services.py::block_user.
    """
    user.set_password(new_password)
    # An admin-created account that resets its own password has chosen one —
    # the forced first-login change no longer applies.
    user.must_change_password = False
    user.save(update_fields=['password', 'must_change_password'])

    for outstanding in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=outstanding)
