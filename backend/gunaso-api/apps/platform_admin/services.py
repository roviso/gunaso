"""Business logic for the platform-superadmin dashboard, kept out of views
per CLAUDE.md section 12.

Every mutating action here appends an immutable PlatformAuditLog row —
mirrors the StatusUpdate/StaffInvite append-only pattern elsewhere in the
codebase. God-mode power, with a trail.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Avg, Count, F
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from .models import PlatformAuditLog

User = get_user_model()


def _log(actor, action: str, target, note: str = '') -> PlatformAuditLog:
    return PlatformAuditLog.objects.create(
        actor=actor,
        action=action,
        target_type=target.__class__.__name__.lower(),
        target_id=target.pk,
        target_repr=str(target)[:255],
        note=note,
    )


def _revoke_all_sessions(user) -> None:
    """Blacklist every outstanding refresh token for `user`. Defense in depth
    alongside the `is_active` check that `JWTAuthentication`/`RefreshView`
    already re-evaluate from the database on every request — a blocked
    user's existing access token is already rejected without this, but this
    also stops a queued-up refresh from minting a new one."""
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)


def verify_organization(org, actor, verified: bool):
    org.is_verified = verified
    org.save(update_fields=['is_verified'])
    _log(actor, 'organization_verified' if verified else 'organization_unverified', org)
    return org


def set_organization_active(org, actor, is_active: bool):
    org.is_active = is_active
    org.save(update_fields=['is_active'])
    _log(actor, 'organization_activated' if is_active else 'organization_deactivated', org)
    return org


def block_user(user, actor):
    if user.id == actor.id:
        raise ValidationError({'detail': 'You cannot block your own account.'})
    with transaction.atomic():
        user.is_active = False
        user.save(update_fields=['is_active'])
        _revoke_all_sessions(user)
        _log(actor, 'user_blocked', user)
    return user


def unblock_user(user, actor):
    user.is_active = True
    user.save(update_fields=['is_active'])
    _log(actor, 'user_unblocked', user)
    return user


def promote_to_superadmin(user, actor):
    user.is_staff = True
    user.is_superuser = True
    user.save(update_fields=['is_staff', 'is_superuser'])
    _log(actor, 'user_promoted', user)
    return user


def demote_superadmin(user, actor):
    if user.id == actor.id:
        raise ValidationError({'detail': 'You cannot demote your own account.'})
    if not user.is_superuser:
        raise ValidationError({'detail': 'This user is not a superadmin.'})
    if User.objects.filter(is_superuser=True).count() <= 1:
        raise ValidationError({'detail': 'Cannot demote the last remaining superadmin.'})
    user.is_staff = False
    user.is_superuser = False
    user.save(update_fields=['is_staff', 'is_superuser'])
    _log(actor, 'user_demoted', user)
    return user


def platform_overview() -> dict:
    """Aggregate cross-platform metrics for the superadmin dashboard overview."""
    from apps.organizations.models import Organization
    from apps.submissions.models import Submission

    now = timezone.now()
    orgs = Organization.objects.all()
    users = User.objects.all()
    submissions = Submission.objects.all()

    by_status = {s: 0 for s, _ in Submission.STATUS_CHOICES}
    by_status.update(dict(
        submissions.values_list('status').annotate(count=Count('id')).order_by()
    ))

    by_user_type = {t: 0 for t, _ in User.USER_TYPE_CHOICES}
    by_user_type.update(dict(
        users.values_list('user_type').annotate(count=Count('id')).order_by()
    ))

    avg_resolution = (
        submissions.filter(resolved_at__isnull=False)
        .annotate(duration=F('resolved_at') - F('created_at'))
        .aggregate(avg=Avg('duration'))['avg']
    )
    avg_resolution_days = round(avg_resolution.total_seconds() / 86400, 1) if avg_resolution else 0

    # Daily submission/signup counts for the last 30 days.
    trend = []
    for days_ago in range(29, -1, -1):
        day_start = (now - timedelta(days=days_ago)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        trend.append({
            'date': day_start.date().isoformat(),
            'submissions': submissions.filter(created_at__gte=day_start, created_at__lt=day_end).count(),
            'users': users.filter(date_joined__gte=day_start, date_joined__lt=day_end).count(),
        })

    return {
        'organizations': {
            'total': orgs.count(),
            'verified': orgs.filter(is_verified=True).count(),
            'unverified': orgs.filter(is_verified=False).count(),
            'active': orgs.filter(is_active=True).count(),
            'inactive': orgs.filter(is_active=False).count(),
        },
        'users': {
            'total': users.count(),
            'active': users.filter(is_active=True).count(),
            'blocked': users.filter(is_active=False).count(),
            'superadmins': users.filter(is_superuser=True).count(),
            'by_type': by_user_type,
        },
        'submissions': {
            'total': submissions.count(),
            'by_status': by_status,
            'avg_resolution_days': avg_resolution_days,
        },
        'trend': trend,
    }
