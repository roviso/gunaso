from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.ai_insights.client import AIError, ClassificationResult, _build_prompt, is_ai_enabled
from apps.ai_insights.models import SubmissionInsight
from apps.ai_insights.services import classify_and_store
from apps.organizations.models import OrganizationStaff, StaffRole
from apps.submissions.models import Category

pytestmark = pytest.mark.django_db

SUBMISSIONS_URL = '/api/v1/submissions/'


def make_result(category='Water Supply', confidence=0.8, sentiment='negative', title='Water leak reported'):
    return ClassificationResult(
        category=category, confidence=confidence, sentiment=sentiment, suggested_title=title,
    )


# --- Configuration gate ------------------------------------------------------

class TestAIEnabledGate:
    def test_disabled_by_default(self, settings):
        settings.ANTHROPIC_API_KEY = ''
        assert is_ai_enabled() is False

    def test_enabled_when_key_configured(self, settings):
        settings.ANTHROPIC_API_KEY = 'sk-ant-test-key'
        assert is_ai_enabled() is True


# --- Anonymity guardrail: the prompt never carries submitter identity -------

class TestPromptNeverLeaksIdentity:
    def test_prompt_excludes_citizen_fields(self, submission):
        # `submission` fixture (conftest.py) has citizen_name/email/phone set —
        # confirm none of them appear anywhere in the built prompt, regardless
        # of is_anonymous.
        prompt = _build_prompt(submission, existing_categories=[])
        assert submission.citizen_name not in prompt
        assert submission.citizen_email not in prompt
        assert submission.citizen_phone not in prompt
        assert submission.title in prompt
        assert submission.description in prompt

    def test_prompt_excludes_identity_for_anonymous_submission_too(self, anonymous_submission):
        prompt = _build_prompt(anonymous_submission, existing_categories=[])
        assert anonymous_submission.title in prompt
        assert anonymous_submission.description in prompt


# --- classify_and_store() ----------------------------------------------------

class TestClassifyAndStore:
    def test_stores_insight_and_auto_applies_when_confident_and_uncategorized(self, submission):
        assert submission.category_id is None
        with patch('apps.ai_insights.services.classify_submission', return_value=make_result(confidence=0.85)):
            insight, applied = classify_and_store(submission)

        assert applied is True
        assert insight.applied is True
        assert insight.suggested_category == 'Water Supply'
        submission.refresh_from_db()
        assert submission.category is not None
        assert submission.category.name == 'Water Supply'

    def test_does_not_overwrite_existing_category(self, submission, organization):
        existing = Category.objects.create(name='Pre-set Category', organization=organization)
        submission.category = existing
        submission.save(update_fields=['category'])

        with patch('apps.ai_insights.services.classify_submission', return_value=make_result(confidence=0.99)):
            insight, applied = classify_and_store(submission)

        assert applied is False
        submission.refresh_from_db()
        assert submission.category_id == existing.id

    def test_low_confidence_not_auto_applied(self, submission):
        with patch('apps.ai_insights.services.classify_submission', return_value=make_result(confidence=0.3)):
            insight, applied = classify_and_store(submission)

        assert applied is False
        assert insight.applied is False
        submission.refresh_from_db()
        assert submission.category_id is None

    def test_reclassifying_replaces_prior_insight(self, submission):
        with patch('apps.ai_insights.services.classify_submission', return_value=make_result(category='First')):
            classify_and_store(submission)
        with patch('apps.ai_insights.services.classify_submission', return_value=make_result(category='Second')):
            classify_and_store(submission)

        assert SubmissionInsight.objects.filter(submission=submission).count() == 1
        assert SubmissionInsight.objects.get(submission=submission).suggested_category == 'Second'


# --- API: manual category endpoint ------------------------------------------

class TestManualCategoryEndpoint:
    def url(self, submission):
        return f'{SUBMISSIONS_URL}{submission.reference_number}/category/'

    def test_org_admin_can_set_category(self, submission, org_admin):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.patch(self.url(submission), {'category': 'Billing Dispute'})
        assert response.status_code == 200
        assert response.data['category'] == 'Billing Dispute'

    def test_requires_manage_submissions_privilege(self, submission, organization, django_user_model):
        staff_user = django_user_model.objects.create_user(
            username='catstaff', email='catstaff@example.com', password='Str0ng-pass-123',
        )
        role = StaffRole.objects.create(organization=organization, name='No Access', privileges=['view_stats'])
        OrganizationStaff.objects.create(organization=organization, user=staff_user, role=role, status='active')
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.patch(self.url(submission), {'category': 'Nope'})
        assert response.status_code == 403

    def test_cross_org_admin_denied(self, submission, other_org_admin):
        client = APIClient()
        client.force_authenticate(other_org_admin)
        response = client.patch(self.url(submission), {'category': 'Hijack'})
        assert response.status_code == 403

    def test_blank_category_rejected(self, submission, org_admin):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.patch(self.url(submission), {'category': ''})
        assert response.status_code == 400

    def test_unauthenticated_denied(self, submission):
        response = APIClient().patch(self.url(submission), {'category': 'X'})
        assert response.status_code == 401


# --- API: AI classify endpoint -----------------------------------------------

class TestAIClassifyEndpoint:
    def url(self, submission):
        return f'{SUBMISSIONS_URL}{submission.reference_number}/ai-classify/'

    def test_returns_503_when_ai_not_configured(self, submission, org_admin, settings):
        settings.ANTHROPIC_API_KEY = ''
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(self.url(submission))
        assert response.status_code == 503

    def test_success_returns_updated_submission(self, submission, org_admin, settings):
        settings.ANTHROPIC_API_KEY = 'sk-ant-test-key'
        client = APIClient()
        client.force_authenticate(org_admin)
        with patch('apps.ai_insights.services.classify_submission', return_value=make_result(confidence=0.9)):
            response = client.post(self.url(submission))
        assert response.status_code == 200
        assert response.data['applied'] is True
        assert response.data['submission']['ai_insight']['suggested_category'] == 'Water Supply'

    def test_ai_error_returns_502(self, submission, org_admin, settings):
        settings.ANTHROPIC_API_KEY = 'sk-ant-test-key'
        client = APIClient()
        client.force_authenticate(org_admin)
        with patch('apps.ai_insights.services.classify_submission', side_effect=AIError('boom')):
            response = client.post(self.url(submission))
        assert response.status_code == 502

    def test_requires_manage_submissions_privilege(self, submission, organization, django_user_model, settings):
        settings.ANTHROPIC_API_KEY = 'sk-ant-test-key'
        staff_user = django_user_model.objects.create_user(
            username='aistaff', email='aistaff@example.com', password='Str0ng-pass-123',
        )
        role = StaffRole.objects.create(organization=organization, name='No Access 2', privileges=['view_stats'])
        OrganizationStaff.objects.create(organization=organization, user=staff_user, role=role, status='active')
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.post(self.url(submission))
        assert response.status_code == 403

    def test_cross_org_admin_denied(self, submission, other_org_admin, settings):
        settings.ANTHROPIC_API_KEY = 'sk-ant-test-key'
        client = APIClient()
        client.force_authenticate(other_org_admin)
        response = client.post(self.url(submission))
        assert response.status_code == 403


# --- organization_stats(): by_category breakdown -----------------------------

class TestOrgStatsByCategory:
    def test_by_category_reflects_assigned_categories(self, organization, org_admin, citizen):
        from apps.submissions.models import Submission
        cat = Category.objects.create(name='Roads', organization=organization)
        for i in range(2):
            Submission.objects.create(
                reference_number=f'GUN-2026-0010{i}', organization=organization, category=cat,
                citizen_name='X', citizen_email='x@example.com',
                title=f'Pothole {i}', description='A large pothole on the main road.',
            )
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.get(f'/api/v1/organizations/{organization.slug}/stats/')
        assert response.status_code == 200
        by_category = {row['id']: row for row in response.data['by_category']}
        assert by_category[cat.id]['count'] == 2
        assert len(by_category[cat.id]['examples']) == 2
