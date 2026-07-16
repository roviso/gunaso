"""Business logic for account-level flows that don't belong in views/serializers
per CLAUDE.md section 12: email verification for accounts whose address was
typed by someone else (an org admin creating staff with admin-set credentials).

Stateless, signed tokens (django.core.signing) are used instead of a DB-backed
model like StaffInvite — verifying twice is harmless (idempotent), so there is
no need to track/invalidate prior tokens the way the single-use staff invite
flow does.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import send_mail

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
