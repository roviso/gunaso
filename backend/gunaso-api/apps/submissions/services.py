"""Business logic for submissions, kept out of views and serializers."""
import secrets

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import InvalidStatusTransitionError, StatusUpdate, Submission

_REFERENCE_ATTEMPTS = 20


def generate_reference_number() -> str:
    """
    Random (non-enumerable) reference of the form GUN-YYYY-NNNNN.
    Falls back to a longer hex token if the 5-digit space is saturated.
    """
    year = timezone.now().year
    for _ in range(_REFERENCE_ATTEMPTS):
        candidate = f'GUN-{year}-{secrets.randbelow(100000):05d}'
        if not Submission.objects.filter(reference_number=candidate).exists():
            return candidate
    return f'GUN-{year}-{secrets.token_hex(4).upper()}'


def create_submission(validated_data: dict, citizen=None) -> Submission:
    """Create a submission with a collision-safe reference number."""
    for _ in range(_REFERENCE_ATTEMPTS):
        try:
            with transaction.atomic():
                return Submission.objects.create(
                    reference_number=generate_reference_number(),
                    citizen=citizen,
                    **validated_data,
                )
        except IntegrityError:
            continue
    raise IntegrityError('Could not allocate a unique reference number.')


def transition_status(submission: Submission, new_status: str, changed_by, note: str = '') -> Submission:
    """
    Apply a validated status transition and append an audit record.
    Raises InvalidStatusTransitionError for disallowed transitions.
    """
    if not submission.can_transition_to(new_status):
        raise InvalidStatusTransitionError(
            f"Cannot transition from '{submission.status}' to '{new_status}'. "
            f"Allowed: {sorted(Submission.VALID_TRANSITIONS.get(submission.status, set()))}"
        )

    old_status = submission.status
    with transaction.atomic():
        submission.status = new_status
        update_fields = ['status', 'updated_at']
        if new_status == 'resolved':
            submission.resolved_at = timezone.now()
            update_fields.append('resolved_at')
        submission.save(update_fields=update_fields)
        StatusUpdate.objects.create(
            submission=submission,
            updated_by=changed_by,
            old_status=old_status,
            new_status=new_status,
            note=note,
        )
    return submission


def organization_stats(organization) -> dict:
    """Aggregate dashboard metrics for one organization."""
    from datetime import timedelta

    from django.db.models import Avg, Count, F

    from apps.organizations.models import OrganizationStaff

    submissions = Submission.objects.filter(organization=organization)

    # Ensure every status/type/priority key is always present (zero if no data).
    by_status = {s: 0 for s, _ in Submission.STATUS_CHOICES}
    by_status.update(dict(
        submissions.values_list('status').annotate(count=Count('id')).order_by()
    ))

    by_type = {t: 0 for t, _ in Submission.TYPE_CHOICES}
    by_type.update(dict(
        submissions.values_list('submission_type').annotate(count=Count('id')).order_by()
    ))

    by_priority = {p: 0 for p, _ in Submission.PRIORITY_CHOICES}
    by_priority.update(dict(
        submissions.values_list('priority').annotate(count=Count('id')).order_by()
    ))

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    resolved_this_month = submissions.filter(resolved_at__gte=month_start).count()

    avg_resolution = (
        submissions.filter(resolved_at__isnull=False)
        .annotate(duration=F('resolved_at') - F('created_at'))
        .aggregate(avg=Avg('duration'))['avg']
    )
    avg_resolution_hours = round(avg_resolution.total_seconds() / 3600, 1) if avg_resolution else 0
    avg_resolution_days = round(avg_resolution.total_seconds() / 86400, 1) if avg_resolution else 0

    # Last 5 status-change events across the org.
    recent_updates = (
        StatusUpdate.objects.filter(submission__organization=organization)
        .select_related('submission', 'updated_by')
        .order_by('-created_at')[:5]
    )
    recent_activity = [
        {
            'reference': u.submission.reference_number,
            'title': u.submission.title,
            'old_status': u.old_status,
            'new_status': u.new_status,
            'updated_by': (
                u.updated_by.get_full_name() or u.updated_by.username
                if u.updated_by else 'System'
            ),
            'timestamp': u.created_at.isoformat(),
        }
        for u in recent_updates
    ]

    staff_count = OrganizationStaff.objects.filter(
        organization=organization, is_active=True
    ).count()

    active_statuses = {'submitted', 'acknowledged', 'in_review', 'escalated'}
    unassigned_count = submissions.filter(
        assigned_to__isnull=True, status__in=active_statuses
    ).count()

    # Daily submission counts for the last 7 days.
    trend = []
    for days_ago in range(6, -1, -1):
        day_start = (now - timedelta(days=days_ago)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day_end = day_start + timedelta(days=1)
        count = submissions.filter(created_at__gte=day_start, created_at__lt=day_end).count()
        trend.append({'date': day_start.date().isoformat(), 'count': count})

    return {
        'organization': organization.name,
        'total': submissions.count(),
        'pending': by_status.get('submitted', 0) + by_status.get('acknowledged', 0),
        'in_review': by_status.get('in_review', 0),
        'resolved': by_status.get('resolved', 0),
        'escalated': by_status.get('escalated', 0),
        'resolved_this_month': resolved_this_month,
        'avg_resolution_hours': avg_resolution_hours,
        'avg_resolution_days': avg_resolution_days,
        'by_status': by_status,
        'by_type': by_type,
        'by_priority': by_priority,
        'recent_activity': recent_activity,
        'staff_count': staff_count,
        'unassigned_count': unassigned_count,
        'trend': trend,
    }
