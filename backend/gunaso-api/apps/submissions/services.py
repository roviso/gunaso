"""Business logic for submissions, kept out of views and serializers."""
import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, F, Q
from django.utils import timezone

from .models import Category, InvalidStatusTransitionError, StatusUpdate, Submission

_REFERENCE_ATTEMPTS = 20
_DERIVED_TITLE_MAX = 60

ACTIVE_STATUSES = ('submitted', 'acknowledged', 'in_review', 'escalated')
# Statuses in which the citizen may rate how their gunaso was handled.
FEEDBACK_STATUSES = ('resolved', 'rejected', 'closed')


class FollowUpError(Exception):
    """A citizen follow-up (reply / satisfaction rating) that isn't allowed in
    the submission's current state. Carries a user-safe message."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


# ─── Private follow-up key ─────────────────────────────────────────────────────
#
# The reference number is only a *locator* — anyone holding it can read the
# public track page, and its 5-digit space is small. Replying to a case or
# rating its outcome needs a real capability, so every submission gets a
# random key that is shown to the submitter exactly once (create response +
# confirmation email) and stored only as a SHA-256 hash, like StaffInvite.

def _hash_followup_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode('utf-8')).hexdigest()


def issue_followup_key(submission: Submission) -> str:
    raw_key = secrets.token_urlsafe(24)
    submission.followup_key_hash = _hash_followup_key(raw_key)
    submission.save(update_fields=['followup_key_hash'])
    return raw_key


def has_followup_access(submission: Submission, user=None, raw_key: str = '') -> bool:
    """The submitter may follow up: either the signed-in owner, or whoever
    holds the private key. Constant-time comparison on the hash."""
    if user is not None and user.is_authenticated and submission.citizen_id == user.id:
        return True
    if raw_key and submission.followup_key_hash:
        return hmac.compare_digest(_hash_followup_key(raw_key), submission.followup_key_hash)
    return False


def derive_title(description: str) -> str:
    """Fallback title for the simplified "what is your gunaso?" submit flow,
    where title is optional — the first sentence/clause of the description,
    trimmed to a word boundary. Never raises; a blank description yields a
    generic placeholder rather than an empty title (the model requires one).
    """
    text = ' '.join((description or '').split())
    if not text:
        return 'Gunaso'
    # Prefer the first sentence-like clause over a hard character cut.
    for sep in ('.', '।', '\n'):
        idx = text.find(sep)
        if 0 < idx <= _DERIVED_TITLE_MAX:
            return text[:idx].strip()
    if len(text) <= _DERIVED_TITLE_MAX:
        return text
    truncated = text[:_DERIVED_TITLE_MAX].rsplit(' ', 1)[0]
    return f'{truncated}…' if truncated else f'{text[:_DERIVED_TITLE_MAX]}…'


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


def resolve_or_create_category(organization, name: str) -> Category:
    """Look up a category by (case-insensitive) name, scoped to `organization`
    then falling back to the global catalog, creating an org-scoped one if
    neither exists. Shared by the citizen-facing create flow and AI
    classification (apps/ai_insights) so both resolve categories identically.
    """
    name = name.strip()
    category = Category.objects.filter(
        name__iexact=name, organization=organization
    ).first() or Category.objects.filter(
        name__iexact=name, organization=None
    ).first()
    if category is None:
        category = Category.objects.create(name=name, organization=organization)
    return category


def create_submission(validated_data: dict, citizen=None) -> Submission:
    """Create a submission with a collision-safe reference number, issue its
    private follow-up key and queue the confirmation email.

    The raw key is attached as `submission.followup_key` for the create
    response only — it is never persisted in plain form.
    """
    from .notifications import notify_submission_received

    for _ in range(_REFERENCE_ATTEMPTS):
        try:
            with transaction.atomic():
                submission = Submission.objects.create(
                    reference_number=generate_reference_number(),
                    citizen=citizen,
                    **validated_data,
                )
                raw_key = issue_followup_key(submission)
            submission.followup_key = raw_key
            notify_submission_received(submission, raw_key)
            return submission
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
        update = StatusUpdate.objects.create(
            submission=submission,
            updated_by=changed_by,
            kind=StatusUpdate.KIND_STATUS_CHANGE,
            old_status=old_status,
            new_status=new_status,
            note=note,
        )
    from .notifications import notify_submission_update
    notify_submission_update(submission, update)
    return submission


def add_staff_note(submission: Submission, note: str, author, internal: bool = False) -> StatusUpdate:
    """Append a staff reply (visible to the citizen, who is emailed) or an
    internal note (organization-only, never emailed or shown publicly)."""
    update = StatusUpdate.objects.create(
        submission=submission,
        updated_by=author,
        kind=StatusUpdate.KIND_INTERNAL_NOTE if internal else StatusUpdate.KIND_NOTE,
        old_status=submission.status,
        new_status=submission.status,
        note=note,
    )
    Submission.objects.filter(pk=submission.pk).update(updated_at=timezone.now())
    if not internal:
        from .notifications import notify_submission_update
        notify_submission_update(submission, update)
    return update


def add_citizen_reply(submission: Submission, message: str, user=None) -> StatusUpdate:
    """Append a follow-up from the submitter. Callers must have checked
    `has_followup_access` first.

    `updated_by` is only ever the signed-in *owner* — never whoever happens to
    be signed in while using a key — so an anonymous submission can't be tied
    back to an account through its replies.
    """
    if submission.status == 'closed':
        raise FollowUpError('This case is closed. Please submit a new gunaso if the problem continues.')
    author = user if (user is not None and user.is_authenticated and submission.citizen_id == user.id) else None
    update = StatusUpdate.objects.create(
        submission=submission,
        updated_by=author,
        kind=StatusUpdate.KIND_CITIZEN_REPLY,
        old_status=submission.status,
        new_status=submission.status,
        note=message,
    )
    Submission.objects.filter(pk=submission.pk).update(updated_at=timezone.now())
    return update


def record_satisfaction(submission: Submission, score: int, comment: str = '') -> Submission:
    """The citizen rates how their gunaso was handled (1–5). Only once the
    organization has reached an outcome; re-rating overwrites."""
    if submission.status not in FEEDBACK_STATUSES:
        raise FollowUpError('You can rate the outcome once the organization has resolved or closed your case.')
    submission.satisfaction_score = score
    submission.satisfaction_comment = comment
    submission.satisfaction_at = timezone.now()
    submission.save(update_fields=['satisfaction_score', 'satisfaction_comment', 'satisfaction_at'])
    return submission


# ─── Service-level targets (SLA) ───────────────────────────────────────────────
#
# Global targets from settings; no background job escalates anything yet
# (Celery Beat is on the roadmap) — overdue cases are surfaced to staff instead.

def _sla_cutoffs(now=None):
    now = now or timezone.now()
    return (
        now - timedelta(hours=settings.SLA_RESPONSE_HOURS),
        now - timedelta(days=settings.SLA_RESOLUTION_DAYS),
    )


def overdue_q(now=None) -> Q:
    """Unacknowledged past the response target, or still open past the
    resolution target."""
    response_cutoff, resolution_cutoff = _sla_cutoffs(now)
    return (
        Q(status='submitted', created_at__lt=response_cutoff)
        | Q(status__in=ACTIVE_STATUSES, created_at__lt=resolution_cutoff)
    )


def is_overdue(submission: Submission, now=None) -> bool:
    if submission.status not in ACTIVE_STATUSES:
        return False
    response_cutoff, resolution_cutoff = _sla_cutoffs(now)
    if submission.status == 'submitted' and submission.created_at < response_cutoff:
        return True
    return submission.created_at < resolution_cutoff


def organization_stats(organization) -> dict:
    """Aggregate dashboard metrics for one organization."""
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

    by_branch = [
        {'id': row['branch__id'], 'name': row['branch__name'], 'count': row['count']}
        for row in (
            submissions.filter(branch__isnull=False)
            .values('branch__id', 'branch__name')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
    ]

    # "What's actually wrong" panel: top categories by volume, each with a
    # few example reference numbers to click into. Purely a DB aggregation
    # over already-assigned categories (manual or AI, see apps.ai_insights) —
    # no live LLM call on every dashboard load.
    by_category = [
        {
            'id': row['category__id'],
            'name': row['category__name'],
            'count': row['count'],
            'examples': list(
                submissions.filter(category_id=row['category__id'])
                .order_by('-created_at')
                .values_list('reference_number', flat=True)[:3]
            ),
        }
        for row in (
            submissions.filter(category__isnull=False)
            .values('category__id', 'category__name')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
    ]

    unassigned_count = submissions.filter(
        assigned_to__isnull=True, status__in=ACTIVE_STATUSES
    ).count()
    overdue_count = submissions.filter(overdue_q(now)).count()

    satisfaction = submissions.filter(satisfaction_score__isnull=False).aggregate(
        avg=Avg('satisfaction_score'), count=Count('id'),
    )
    total = submissions.count()
    closed_out = by_status.get('resolved', 0) + by_status.get('closed', 0)

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
        'total': total,
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
        'overdue_count': overdue_count,
        'resolution_rate': round(closed_out * 100 / total) if total else 0,
        'satisfaction_avg': round(float(satisfaction['avg']), 1) if satisfaction['avg'] is not None else None,
        'satisfaction_count': satisfaction['count'],
        'sla': {
            'response_hours': settings.SLA_RESPONSE_HOURS,
            'resolution_days': settings.SLA_RESOLUTION_DAYS,
        },
        'trend': trend,
        'by_branch': by_branch,
        'by_category': by_category,
    }


PUBLIC_STATS_CACHE_KEY = 'public-platform-stats'
PUBLIC_STATS_CACHE_SECONDS = 300


def public_platform_stats() -> dict:
    """Aggregate, identity-free platform numbers for the landing page and
    transparency sections. Counts only — never titles or content — and only
    for verified, active organizations. Cached briefly: it runs on every
    landing-page visit."""
    cached = cache.get(PUBLIC_STATS_CACHE_KEY)
    if cached is not None:
        return cached

    from apps.organizations.models import Branch, Organization

    orgs = Organization.objects.filter(is_active=True, is_verified=True)
    submissions = Submission.objects.filter(organization__in=orgs)
    total = submissions.count()
    closed_out = submissions.filter(status__in=['resolved', 'closed']).count()
    avg_resolution = (
        submissions.filter(resolved_at__isnull=False)
        .annotate(duration=F('resolved_at') - F('created_at'))
        .aggregate(avg=Avg('duration'))['avg']
    )
    satisfaction = submissions.filter(satisfaction_score__isnull=False).aggregate(
        avg=Avg('satisfaction_score'), count=Count('id'),
    )
    since = timezone.now() - timedelta(days=30)

    stats = {
        'organizations': orgs.count(),
        'branches': Branch.objects.filter(organization__in=orgs, is_active=True).count(),
        'submissions': total,
        'resolved': closed_out,
        'resolution_rate': round(closed_out * 100 / total) if total else 0,
        'in_progress': submissions.filter(status__in=ACTIVE_STATUSES).count(),
        'submissions_last_30_days': submissions.filter(created_at__gte=since).count(),
        'avg_resolution_days': round(avg_resolution.total_seconds() / 86400, 1) if avg_resolution else None,
        'satisfaction_avg': round(float(satisfaction['avg']), 1) if satisfaction['avg'] is not None else None,
        'satisfaction_count': satisfaction['count'],
        'by_type': {
            t: submissions.filter(submission_type=t).count() for t, _ in Submission.TYPE_CHOICES
        },
    }
    cache.set(PUBLIC_STATS_CACHE_KEY, stats, PUBLIC_STATS_CACHE_SECONDS)
    return stats
