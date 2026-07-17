"""Business logic for the staff invite / invite-link onboarding flow.

Kept out of views and serializers per CLAUDE.md section 12. Two entry points
matter to callers:

- `create_or_invite_staff` — used by `OrganizationStaffView.post`. Attaches an
  existing, usable-password user immediately, or creates a pending user +
  emails a single-use invite link.
- `accept_invite` — used by the public accept endpoint, mirrors
  `apps.accounts.views.RegisterView` so the frontend can reuse its
  session-setting logic afterwards.

Raw invite tokens are never persisted — only their sha256 hash
(`StaffInvite.token_hash`) is. The raw token exists only in memory long
enough to build the emailed link.
"""
import hashlib
import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Organization, OrganizationRating, OrganizationStaff, StaffInvite, StaffRole

User = get_user_model()


def rate_organization(org: Organization, user, score: int) -> OrganizationRating:
    """Upsert the user's rating for this organization (one row per user per org)."""
    rating, _created = OrganizationRating.objects.update_or_create(
        organization=org, user=user, defaults={'score': score},
    )
    return rating


class InviteError(Exception):
    """Base class for invite-resolution failures. Carries a user-safe message."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InviteInvalidError(InviteError):
    """Token doesn't exist, or has already been accepted."""


class InviteExpiredError(InviteError):
    """Token exists and is unaccepted, but its expiry has passed."""


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()


def _generate_raw_token() -> str:
    """Cryptographically secure, URL-safe — never logged, never stored raw."""
    return secrets.token_urlsafe(32)


def _invite_expiry() -> timezone.datetime:
    days = getattr(settings, 'STAFF_INVITE_EXPIRY_DAYS', 7)
    return timezone.now() + timedelta(days=days)


def _unique_username(email: str) -> str:
    """Mirrors UserRegistrationSerializer._unique_username."""
    base = re.sub(r'[^a-z0-9_.]', '', email.split('@')[0].lower()) or 'user'
    username = base
    suffix = 1
    while User.objects.filter(username=username).exists():
        suffix += 1
        username = f'{base}{suffix}'
    return username


def invite_link(raw_token: str) -> str:
    """Public helper so callers (views) can show the link as a copy fallback
    when email delivery isn't configured or didn't reach the inbox. Must match
    the frontend route in router/index.js exactly — `/invite/:token`."""
    frontend = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
    return f'{frontend.rstrip("/")}/invite/{raw_token}'


def send_staff_invite_email(staff: OrganizationStaff, raw_token: str, expires_at) -> None:
    """Emails the single-use invite link. Uses send_mail so this works unchanged
    against the console backend in dev and django.core.mail.outbox in tests."""
    org = staff.organization
    role_name = staff.role.name if staff.role else 'a staff member'
    link = invite_link(raw_token)
    subject = f'You have been invited to join {org.name} on Gunaso'
    message = (
        f'Hi,\n\n'
        f'You have been invited to join {org.name} on Gunaso as {role_name}.\n\n'
        f'Set your password to accept the invite and get started:\n{link}\n\n'
        f'This link expires on {expires_at:%Y-%m-%d %H:%M} UTC and can only be used once.\n'
        f'If you were not expecting this invitation, you can safely ignore this email.\n'
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [staff.user.email], fail_silently=False)


def create_or_invite_staff(
    org, email: str, role: StaffRole, assigned_by,
) -> tuple[OrganizationStaff, bool, str | None]:
    """
    Add a staff member by email.

    - An existing, already-usable-password, active user is attached immediately
      (status='active', no invite/email needed).
    - Otherwise a pending user (unusable password, is_active=False if new) is
      created/reused, an OrganizationStaff row is created with status='invited',
      and a single-use expiring StaffInvite is issued and emailed.

    Returns (staff, invited, raw_token). `raw_token` is None for the
    immediate-attach path and must never be logged or returned to the caller
    beyond this function.
    """
    email = (email or '').strip().lower()
    if not email:
        raise ValidationError({'email': 'This field is required.'})

    existing_user = User.objects.filter(email__iexact=email).first()

    if existing_user and OrganizationStaff.objects.filter(organization=org, user=existing_user).exists():
        raise ValidationError({'email': 'This user is already a staff member of this organization.'})

    with transaction.atomic():
        if existing_user and existing_user.is_active and existing_user.has_usable_password():
            staff = OrganizationStaff.objects.create(
                organization=org, user=existing_user, role=role,
                status='active', assigned_by=assigned_by,
            )
            return staff, False, None

        user = existing_user
        if user is None:
            user = User(
                username=_unique_username(email),
                email=email,
                user_type='citizen',
                is_active=False,
            )
            user.set_unusable_password()
            user.save()

        staff = OrganizationStaff.objects.create(
            organization=org, user=user, role=role,
            status='invited', assigned_by=assigned_by,
        )
        raw_token = _generate_raw_token()
        expires_at = _invite_expiry()
        StaffInvite.objects.create(
            staff=staff,
            token_hash=_hash_token(raw_token),
            expires_at=expires_at,
            created_by=assigned_by,
        )

    send_staff_invite_email(staff, raw_token, expires_at)
    return staff, True, raw_token


def create_staff_with_credentials(
    org, username: str, password: str, email: str, role: StaffRole, assigned_by,
) -> OrganizationStaff:
    """Admin sets the initial username + password directly — no working inbox
    required for the staff member to get in. The account is active
    immediately so the admin can hand credentials over out-of-band (in
    person, chat, printed slip), as an alternative to `create_or_invite_staff`.

    Security tradeoffs, deliberately accepted because the admin already
    controls staff onboarding for their own org:
    - `email_verified=False` on the new user — the admin-typed email is
      unproven until the staff member verifies it themselves later
      (see apps.accounts.services / RequestEmailVerificationView).
    - `must_change_password=True` — forces a new, staff-only password on
      first login (apps.accounts.views.ChangePasswordView) so the
      admin-known credential can't remain valid indefinitely.
    """
    username = (username or '').strip()
    email = (email or '').strip().lower()
    if not username:
        raise ValidationError({'username': 'This field is required.'})
    if not email:
        raise ValidationError({'email': 'This field is required.'})
    if not password:
        raise ValidationError({'password': 'This field is required.'})

    try:
        UnicodeUsernameValidator()(username)
    except DjangoValidationError as exc:
        raise ValidationError({'username': list(exc.messages)})

    if User.objects.filter(username__iexact=username).exists():
        raise ValidationError({'username': 'This username is already taken.'})
    if User.objects.filter(email__iexact=email).exists():
        raise ValidationError({'email': 'An account with this email already exists.'})

    temp_user = User(username=username, email=email)
    try:
        validate_password(password, user=temp_user)
    except DjangoValidationError as exc:
        raise ValidationError({'password': list(exc.messages)})

    with transaction.atomic():
        user = User(
            username=username,
            email=email,
            user_type='citizen',
            is_active=True,
            email_verified=False,
            must_change_password=True,
        )
        user.set_password(password)
        user.save()

        staff = OrganizationStaff.objects.create(
            organization=org, user=user, role=role,
            status='active', assigned_by=assigned_by,
        )
    return staff


def resend_staff_invite(staff: OrganizationStaff, created_by) -> tuple[OrganizationStaff, str]:
    """Invalidate any prior unaccepted token for `staff` and issue + email a new one.

    StaffInvite is a OneToOneField to OrganizationStaff, so "invalidate" means
    overwriting the existing row's token_hash/expires_at (the old raw token's
    hash no longer matches anything, so the old link stops working) rather
    than inserting a second row.

    Returns (staff, raw_token) — the raw token lets the caller show a copy-link
    fallback in the admin UI alongside the email.
    """
    if staff.status == 'active':
        raise ValidationError({'staff': 'This staff member is already active.'})

    raw_token = _generate_raw_token()
    expires_at = _invite_expiry()
    StaffInvite.objects.update_or_create(
        staff=staff,
        defaults={
            'token_hash': _hash_token(raw_token),
            'expires_at': expires_at,
            'accepted_at': None,
            'created_by': created_by,
        },
    )
    send_staff_invite_email(staff, raw_token, expires_at)
    return staff, raw_token


def resolve_invite(raw_token: str) -> StaffInvite:
    """Resolve a raw token to its StaffInvite, or raise InviteInvalidError /
    InviteExpiredError. Never distinguishes 'no such token' from 'wrong hash'
    in its error message — that would let an invite be enumerated."""
    token_hash = _hash_token(raw_token)
    try:
        invite = (
            StaffInvite.objects.select_related('staff__organization', 'staff__role', 'staff__user')
            .get(token_hash=token_hash)
        )
    except StaffInvite.DoesNotExist:
        raise InviteInvalidError('This invite link is invalid.')

    if invite.accepted_at is not None:
        raise InviteInvalidError('This invite link has already been used.')
    if invite.expires_at <= timezone.now():
        raise InviteExpiredError('This invite link has expired.')
    return invite


def accept_invite(invite: StaffInvite, password: str):
    """Activate the pending user with the (already-validated) new password,
    mark the staff row active, and stamp the invite as accepted. Returns the
    User so the caller can log them straight in (mirrors RegisterView).

    Password validation itself happens one layer up, in
    `StaffInviteAcceptSerializer.validate` (mirroring
    `UserRegistrationSerializer.validate`) — DRF only auto-converts a Django
    `ValidationError` raised from inside a serializer's `validate()` into an
    HTTP 400; raising it from a plain service function would surface as an
    unhandled 500 instead.
    """
    staff = invite.staff
    user = staff.user

    with transaction.atomic():
        user.set_password(password)
        user.is_active = True
        user.save(update_fields=['password', 'is_active'])

        staff.status = 'active'
        staff.save(update_fields=['status'])

        invite.accepted_at = timezone.now()
        invite.save(update_fields=['accepted_at'])

    return user
