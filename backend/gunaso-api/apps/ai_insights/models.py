from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.submissions.models import Submission


class SubmissionInsight(models.Model):
    """AI-generated classification for one submission — a suggestion, not an
    edit. Auto-applying the suggested category to `Submission.category` (see
    apps/ai_insights/services.py::classify_and_store) only happens when the
    submission had no category yet; an existing citizen- or staff-chosen
    category is never overwritten. One row per submission — re-classifying
    replaces it (see `update_or_create` in services.py).
    """

    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ]

    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, related_name='ai_insight')
    suggested_category = models.CharField(max_length=100)
    confidence = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    sentiment = models.CharField(max_length=10, choices=SENTIMENT_CHOICES)
    suggested_title = models.CharField(max_length=150, blank=True)
    # Whether `suggested_category` was auto-applied to the submission at
    # classification time (submission had no category yet + confidence met
    # the threshold) — lets the dashboard show "AI-assigned" vs. "AI suggests".
    applied = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'submission insight'

    def __str__(self):
        return f'AI insight for {self.submission.reference_number}'


class AISuggestion(models.Model):
    """AI-generated "sujhav" (सुझाव) — a suggested resolution/response for one
    submission, shown to org staff. Bilingual: Nepali first, English below, so
    staff can use either directly. One row per submission; regenerating
    replaces it (see services.py::generate_and_store_sujhav)."""

    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, related_name='ai_suggestion')
    suggestion_nepali = models.TextField()
    suggestion_english = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'AI suggestion'

    def __str__(self):
        return f'AI suggestion for {self.submission.reference_number}'


class AIReport(models.Model):
    """A persisted, browsable AI-generated report summarizing an
    organization's submissions over a date range — themes, sentiment,
    recommendations. Generated on demand (services.py::generate_report);
    kept so staff can revisit past reports rather than re-generating (and
    re-billing) every time.
    """

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='ai_reports')
    date_from = models.DateField()
    date_to = models.DateField()
    submission_count = models.PositiveIntegerField()
    summary_nepali = models.TextField()
    summary_english = models.TextField()
    # [{"name": str, "count": int, "summary": str}, ...]
    themes = models.JSONField(default=list)
    sentiment_overview = models.TextField(blank=True)
    # [str, ...] — concrete, actionable recommendations for the organization.
    recommendations = models.JSONField(default=list)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='ai_reports_created')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'AI report'

    def __str__(self):
        return f'AI report for {self.organization.name} ({self.date_from}–{self.date_to})'
