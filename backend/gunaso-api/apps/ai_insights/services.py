"""Business logic for AI classification — kept out of views per CLAUDE.md
section 12. See client.py for the Anthropic SDK boundary.
"""
from django.db import transaction

from apps.submissions.models import Category, Submission
from apps.submissions.services import resolve_or_create_category

from .client import AIError, classify_submission, generate_report, generate_sujhav, is_ai_enabled
from .models import AIReport, AISuggestion, SubmissionInsight

# Below this confidence, the suggestion is stored but never auto-applied —
# staff review and apply it manually via the category endpoint.
CONFIDENCE_AUTO_APPLY_THRESHOLD = 0.6

# Hard cap on how many submissions feed one report call — bounds token cost
# and latency regardless of how large the selected date range is. Most
# recent first, so a huge range still reports on the freshest activity.
REPORT_SUBMISSION_LIMIT = 150

__all__ = [
    'AIError', 'is_ai_enabled', 'CONFIDENCE_AUTO_APPLY_THRESHOLD', 'REPORT_SUBMISSION_LIMIT',
    'classify_and_store', 'generate_and_store_sujhav', 'generate_and_store_report',
]


def classify_and_store(submission) -> tuple[SubmissionInsight, bool]:
    """Classify one submission and persist the result.

    Auto-applies the suggested category to `submission.category` only when
    the submission has none yet and confidence clears the threshold — an
    existing citizen- or staff-chosen category is never overwritten. Returns
    (insight, applied).
    """
    existing_categories = list(
        Category.objects.filter(organization=submission.organization, is_active=True)
        .values_list('name', flat=True)
    )
    result = classify_submission(submission, existing_categories)

    applied = False
    with transaction.atomic():
        insight, _ = SubmissionInsight.objects.update_or_create(
            submission=submission,
            defaults={
                'suggested_category': result.category,
                'confidence': result.confidence,
                'sentiment': result.sentiment,
                'suggested_title': result.suggested_title,
                'applied': False,
            },
        )
        if submission.category_id is None and result.confidence >= CONFIDENCE_AUTO_APPLY_THRESHOLD:
            submission.category = resolve_or_create_category(submission.organization, result.category)
            submission.save(update_fields=['category', 'updated_at'])
            insight.applied = True
            insight.save(update_fields=['applied'])
            applied = True

    return insight, applied


def generate_and_store_sujhav(submission) -> AISuggestion:
    """Generate (or regenerate) the AI सुझाव for one submission."""
    result = generate_sujhav(submission)
    suggestion, _ = AISuggestion.objects.update_or_create(
        submission=submission,
        defaults={
            'suggestion_nepali': result.suggestion_nepali,
            'suggestion_english': result.suggestion_english,
        },
    )
    return suggestion


def generate_and_store_report(organization, date_from, date_to, created_by) -> AIReport:
    """Summarize `organization`'s submissions created in [date_from, date_to]
    (inclusive) into a persisted AIReport. Only identity-free fields
    (type/category/title/description/status) are sent — see
    apps.ai_insights.client._build_report_prompt.
    """
    submissions = (
        Submission.objects.filter(
            organization=organization,
            created_at__date__gte=date_from,
            created_at__date__lte=date_to,
        )
        .select_related('category')
        .order_by('-created_at')[:REPORT_SUBMISSION_LIMIT]
    )
    submissions_data = [
        {
            'type': s.submission_type,
            'category': s.category.name if s.category_id else 'Uncategorized',
            'title': s.title,
            'description': s.description,
            'status': s.status,
        }
        for s in submissions
    ]

    result = generate_report(organization.name, date_from, date_to, submissions_data)

    return AIReport.objects.create(
        organization=organization,
        date_from=date_from,
        date_to=date_to,
        submission_count=len(submissions_data),
        summary_nepali=result.summary_nepali,
        summary_english=result.summary_english,
        themes=[theme.model_dump() for theme in result.themes],
        sentiment_overview=result.sentiment_overview,
        recommendations=result.recommendations,
        created_by=created_by,
    )
