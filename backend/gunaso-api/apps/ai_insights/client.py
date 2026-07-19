"""Thin wrapper around the Anthropic SDK for submission classification.

Kept separate from services.py so the network/SDK boundary is easy to mock in
tests (patch `classify_submission`) without touching the persistence logic.
"""
import logging
from typing import Literal

from django.conf import settings
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AIError(Exception):
    """AI features are unconfigured, or the classification call failed."""


class ClassificationResult(BaseModel):
    category: str = Field(
        description='Best-fit category name, preferring one from the provided '
                    'existing-categories list; a short new one (2-4 words) if none fit.'
    )
    confidence: float = Field(ge=0, le=1)
    sentiment: Literal['positive', 'neutral', 'negative']
    suggested_title: str = Field(max_length=150)


class SujhavResult(BaseModel):
    """AI-suggested resolution/response for one submission, bilingual."""
    suggestion_nepali: str = Field(description='Suggested resolution steps or response, in Nepali.')
    suggestion_english: str = Field(description='The same suggestion, in English.')


class ReportThemeItem(BaseModel):
    name: str
    count: int = Field(ge=0)
    summary: str = Field(description='One or two sentences on this theme.')


class ReportResult(BaseModel):
    """Org-wide summary of submissions over a date range."""
    summary_nepali: str = Field(description='Executive summary of the period, in Nepali.')
    summary_english: str = Field(description='The same executive summary, in English.')
    themes: list[ReportThemeItem] = Field(description='Recurring themes across the submissions, most common first.')
    sentiment_overview: str = Field(description='One paragraph describing the overall sentiment/trend.')
    recommendations: list[str] = Field(description='Concrete, actionable recommendations for the organization.')


def is_ai_enabled() -> bool:
    return bool(getattr(settings, 'ANTHROPIC_API_KEY', ''))


def _client():
    if not is_ai_enabled():
        raise AIError('AI features are not configured for this deployment.')
    import anthropic
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _build_prompt(submission, existing_categories: list[str]) -> str:
    # Only type/title/description — never citizen_name/email/phone, regardless
    # of is_anonymous. Submitter identity must never leave the platform.
    categories_line = ', '.join(existing_categories) if existing_categories else '(none yet — propose one)'
    return (
        f'Submission type: {submission.submission_type}\n'
        f'Title: {submission.title}\n'
        f'Description: {submission.description}\n\n'
        f"This organization's existing categories: {categories_line}\n\n"
        'Classify this citizen submission to a civic-tech complaint/feedback platform. '
        'Prefer an existing category if one clearly fits; otherwise propose a short, '
        'clear new one. Rate the sentiment behind the writing, and suggest a concise, '
        'specific title (<=80 characters) summarizing the issue.'
    )


def _build_sujhav_prompt(submission) -> str:
    # Same identity rule as _build_prompt: title/description/type/category only.
    category = submission.category.name if submission.category_id else 'Uncategorized'
    return (
        f'Submission type: {submission.submission_type}\n'
        f'Category: {category}\n'
        f'Title: {submission.title}\n'
        f'Description: {submission.description}\n\n'
        'You are advising the staff of a civic-tech organization on how to respond to '
        "this citizen's submission. Suggest concrete, actionable next steps or a draft "
        'response the staff could send. Write it once in Nepali, then again in English — '
        'both should stand alone (the English is not a translation note, it is a full '
        'independent version staff can use directly).'
    )


def generate_sujhav(submission) -> SujhavResult:
    """One सुझाव (suggestion) call for a single submission."""
    client = _client()
    try:
        response = client.messages.parse(
            model=getattr(settings, 'AI_CLASSIFICATION_MODEL', 'claude-opus-4-8'),
            max_tokens=1536,
            messages=[{'role': 'user', 'content': _build_sujhav_prompt(submission)}],
            output_format=SujhavResult,
        )
    except Exception as exc:
        logger.warning(
            'AI sujhav request failed for submission %s: %s', submission.reference_number, exc,
        )
        raise AIError('The AI suggestion request failed. Please try again.') from exc

    if response.parsed_output is None:
        raise AIError('AI suggestion returned an unusable response.')
    return response.parsed_output


def _build_report_prompt(organization_name: str, date_from, date_to, submissions_data: list[dict]) -> str:
    lines = [
        f'{i}. [{item["type"]}] {item["category"]} — "{item["title"]}" '
        f'(status: {item["status"]}): {item["description"]}'
        for i, item in enumerate(submissions_data, start=1)
    ]
    body = '\n'.join(lines) if lines else '(no submissions in this period)'
    return (
        f'Organization: {organization_name}\n'
        f'Period: {date_from} to {date_to}\n'
        f'Total submissions in period: {len(submissions_data)}\n\n'
        f'Submissions:\n{body}\n\n'
        'Write a period report for this civic-tech organization\'s leadership, based only '
        'on the submissions above. Identify recurring themes with counts, describe the '
        'overall sentiment/trend, and give concrete recommendations. Write the executive '
        'summary once in Nepali and once in English — both full, independent versions.'
    )


def generate_report(organization_name: str, date_from, date_to, submissions_data: list[dict]) -> ReportResult:
    """One report call summarizing a batch of submissions. `submissions_data`
    items must already be identity-free (see services.py::generate_report)."""
    client = _client()
    try:
        response = client.messages.parse(
            model=getattr(settings, 'AI_CLASSIFICATION_MODEL', 'claude-opus-4-8'),
            max_tokens=4096,
            messages=[{
                'role': 'user',
                'content': _build_report_prompt(organization_name, date_from, date_to, submissions_data),
            }],
            output_format=ReportResult,
        )
    except Exception as exc:
        logger.warning('AI report request failed for %s: %s', organization_name, exc)
        raise AIError('The AI report request failed. Please try again.') from exc

    if response.parsed_output is None:
        raise AIError('AI report returned an unusable response.')
    return response.parsed_output


def classify_submission(submission, existing_categories: list[str]) -> ClassificationResult:
    """One classification call for a single submission. Raises AIError on any
    failure (unconfigured, network, or an unparseable response) — callers
    decide how to surface that (see apps/ai_insights/services.py)."""
    client = _client()
    prompt = _build_prompt(submission, existing_categories)

    try:
        response = client.messages.parse(
            model=getattr(settings, 'AI_CLASSIFICATION_MODEL', 'claude-opus-4-8'),
            max_tokens=1024,
            messages=[{'role': 'user', 'content': prompt}],
            output_format=ClassificationResult,
        )
    except Exception as exc:
        logger.warning(
            'AI classification request failed for submission %s: %s',
            submission.reference_number, exc,
        )
        raise AIError('The AI classification request failed. Please try again.') from exc

    if response.parsed_output is None:
        raise AIError('AI classification returned an unusable response.')
    return response.parsed_output
