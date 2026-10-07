"""Citizen-facing email notifications for a submission's lifecycle.

- On creation: a receipt with the reference number and the private
  follow-up link (the only time the raw follow-up key is ever emailed).
- On every status change and every public staff reply: what changed.

Rules:
- Anonymous submissions never have a stored email, and are never emailed —
  checked explicitly anyway, so a future change can't silently start
  mailing someone who asked not to be identified.
- Internal staff notes are never emailed (services.add_staff_note doesn't
  call in here for them).
- Sending happens after the DB transaction commits, and — unless
  NOTIFICATIONS_ASYNC is False (tests) — on a background thread, so a slow
  or unreachable SMTP server can never slow down or fail the API request.
  Failures are logged, never raised.
"""
import logging
import threading

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

SITE_NAME = 'Gunaso'

STATUS_LABELS = {
    'submitted': 'Submitted',
    'acknowledged': 'Acknowledged',
    'in_review': 'In review',
    'resolved': 'Resolved',
    'rejected': 'Rejected',
    'escalated': 'Escalated',
    'closed': 'Closed',
}

STATUS_EXPLAINERS = {
    'acknowledged': 'The organization has received your gunaso and will look into it.',
    'in_review': 'Someone at the organization is actively working on your gunaso.',
    'escalated': 'Your gunaso has been escalated to a more senior team for attention.',
    'resolved': 'The organization has marked your gunaso as resolved. '
                'Please let them know how they did — it takes one click.',
    'rejected': 'The organization has decided not to take action on this gunaso. '
                'Their note, if any, explains why.',
    'closed': 'This case is now closed. If the problem comes back, you can submit a new gunaso any time.',
}


def _frontend_url() -> str:
    return getattr(settings, 'FRONTEND_URL', 'http://localhost:3000').rstrip('/')


def track_link(reference: str, followup_key: str = '') -> str:
    """Public track page link. The private key rides in the URL *fragment*,
    which browsers never send to the server — so it can't end up in access
    logs or a Referer header."""
    link = f'{_frontend_url()}/track/{reference}'
    return f'{link}#key={followup_key}' if followup_key else link


def _recipient(submission) -> str:
    if submission.is_anonymous:
        return ''
    return (submission.citizen_email or '').strip()


def _send(subject: str, template: str, context: dict, to: str) -> None:
    context = {'site_name': SITE_NAME, **context}
    try:
        message = EmailMultiAlternatives(
            subject=subject,
            body=render_to_string(f'email/{template}.txt', context),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to],
        )
        message.attach_alternative(render_to_string(f'email/{template}.html', context), 'text/html')
        message.send(fail_silently=False)
    except Exception:  # noqa: BLE001 — a notification must never break the request
        logger.exception('Failed to send %s notification', template)


def _dispatch(subject: str, template: str, context: dict, to: str) -> None:
    def run():
        if getattr(settings, 'NOTIFICATIONS_ASYNC', True):
            threading.Thread(
                target=_send, args=(subject, template, context, to), daemon=True,
            ).start()
        else:
            _send(subject, template, context, to)

    transaction.on_commit(run)


def notify_submission_received(submission, followup_key: str) -> None:
    to = _recipient(submission)
    if not to:
        return
    org = submission.organization
    _dispatch(
        subject=f'We received your gunaso — {submission.reference_number}',
        template='submission_received',
        context={
            'name': submission.citizen_name or 'there',
            'reference': submission.reference_number,
            'title': submission.title,
            'organization': org.name,
            'branch': submission.branch.name if submission.branch_id else '',
            'private_link': track_link(submission.reference_number, followup_key),
            'response_hours': settings.SLA_RESPONSE_HOURS,
        },
        to=to,
    )


def notify_submission_update(submission, update) -> None:
    """A status change or a public staff reply on `submission`."""
    to = _recipient(submission)
    if not to:
        return
    status_changed = update.old_status != update.new_status
    status_label = STATUS_LABELS.get(update.new_status, update.new_status)
    org_name = submission.organization.name
    if status_changed:
        subject = f'{submission.reference_number}: your gunaso is now "{status_label}"'
        headline = f'Status changed to {status_label}'
    else:
        subject = f'{submission.reference_number}: new reply from {org_name}'
        headline = f'{org_name} replied to your gunaso'
    _dispatch(
        subject=subject,
        template='submission_update',
        context={
            'name': submission.citizen_name or 'there',
            'reference': submission.reference_number,
            'title': submission.title,
            'organization': org_name,
            'headline': headline,
            'status_changed': status_changed,
            'status_label': status_label,
            'explainer': STATUS_EXPLAINERS.get(update.new_status, '') if status_changed else '',
            'note': update.note,
            'link': track_link(submission.reference_number),
            'invite_feedback': update.new_status in ('resolved', 'rejected') and status_changed,
        },
        to=to,
    )
