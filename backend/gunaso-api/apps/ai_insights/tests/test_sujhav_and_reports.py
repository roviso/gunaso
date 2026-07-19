from datetime import date, timedelta
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.ai_insights.client import AIError, ReportResult, ReportThemeItem, SujhavResult, _build_sujhav_prompt
from apps.ai_insights.models import AIReport, AISuggestion
from apps.ai_insights.services import generate_and_store_report, generate_and_store_sujhav
from apps.organizations.models import OrganizationStaff, StaffRole
from apps.submissions.models import Submission

pytestmark = pytest.mark.django_db

SUBMISSIONS_URL = '/api/v1/submissions/'
ORG_URL = '/api/v1/org/'


def make_sujhav_result():
    return SujhavResult(suggestion_nepali='पानी आपूर्ति समस्या समाधान गर्नुहोस्।', suggestion_english='Resolve the water supply issue.')


def make_report_result():
    return ReportResult(
        summary_nepali='यस अवधिमा पानी आपूर्ति सम्बन्धी गुनासोहरू धेरै आए।',
        summary_english='Water supply complaints dominated this period.',
        themes=[ReportThemeItem(name='Water Supply', count=3, summary='Recurring outages.')],
        sentiment_overview='Mostly negative, trending slightly better toward period end.',
        recommendations=['Publish a maintenance schedule.', 'Add an SMS outage alert.'],
    )


# --- Anonymity guardrail for sujhav prompt -----------------------------------

class TestSujhavPromptNeverLeaksIdentity:
    def test_prompt_excludes_citizen_fields(self, submission):
        prompt = _build_sujhav_prompt(submission)
        assert submission.citizen_name not in prompt
        assert submission.citizen_email not in prompt
        assert submission.citizen_phone not in prompt
        assert submission.description in prompt


# --- generate_and_store_sujhav() ---------------------------------------------

class TestGenerateAndStoreSujhav:
    def test_creates_suggestion(self, submission):
        with patch('apps.ai_insights.services.generate_sujhav', return_value=make_sujhav_result()):
            suggestion = generate_and_store_sujhav(submission)
        assert suggestion.suggestion_english == 'Resolve the water supply issue.'
        assert AISuggestion.objects.filter(submission=submission).count() == 1

    def test_regenerating_replaces_prior_suggestion(self, submission):
        with patch('apps.ai_insights.services.generate_sujhav', return_value=make_sujhav_result()):
            generate_and_store_sujhav(submission)
        second = SujhavResult(suggestion_nepali='नयाँ', suggestion_english='Updated suggestion.')
        with patch('apps.ai_insights.services.generate_sujhav', return_value=second):
            generate_and_store_sujhav(submission)
        assert AISuggestion.objects.filter(submission=submission).count() == 1
        assert AISuggestion.objects.get(submission=submission).suggestion_english == 'Updated suggestion.'


# --- API: AI suggestion endpoint ---------------------------------------------

class TestAISuggestionEndpoint:
    def url(self, submission):
        return f'{SUBMISSIONS_URL}{submission.reference_number}/ai-suggestion/'

    def test_returns_503_when_ai_not_configured(self, submission, org_admin, settings):
        settings.ANTHROPIC_API_KEY = ''
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(self.url(submission))
        assert response.status_code == 503

    def test_success_populates_ai_suggestion(self, submission, org_admin, settings):
        settings.ANTHROPIC_API_KEY = 'sk-ant-test-key'
        client = APIClient()
        client.force_authenticate(org_admin)
        with patch('apps.ai_insights.services.generate_sujhav', return_value=make_sujhav_result()):
            response = client.post(self.url(submission))
        assert response.status_code == 200
        assert response.data['ai_suggestion']['suggestion_english'] == 'Resolve the water supply issue.'

    def test_ai_error_returns_502(self, submission, org_admin, settings):
        settings.ANTHROPIC_API_KEY = 'sk-ant-test-key'
        client = APIClient()
        client.force_authenticate(org_admin)
        with patch('apps.ai_insights.services.generate_sujhav', side_effect=AIError('boom')):
            response = client.post(self.url(submission))
        assert response.status_code == 502

    def test_cross_org_admin_denied(self, submission, other_org_admin, settings):
        settings.ANTHROPIC_API_KEY = 'sk-ant-test-key'
        client = APIClient()
        client.force_authenticate(other_org_admin)
        response = client.post(self.url(submission))
        assert response.status_code == 403


# --- generate_and_store_report() ---------------------------------------------

class TestGenerateAndStoreReport:
    def test_creates_report_with_expected_fields(self, organization, org_admin, citizen):
        today = date.today()
        Submission.objects.create(
            reference_number='GUN-2026-00500', organization=organization,
            citizen_name='X', citizen_email='x@example.com',
            title='Water leak', description='Water leaking near the office for days.',
        )
        with patch('apps.ai_insights.services.generate_report', return_value=make_report_result()):
            report = generate_and_store_report(
                organization, today - timedelta(days=7), today, created_by=org_admin,
            )
        assert report.submission_count == 1
        assert report.summary_english == 'Water supply complaints dominated this period.'
        assert report.themes[0]['name'] == 'Water Supply'
        assert 'Publish a maintenance schedule.' in report.recommendations

    def test_report_excludes_citizen_identity_from_prompt_data(self, organization, org_admin):
        today = date.today()
        Submission.objects.create(
            reference_number='GUN-2026-00501', organization=organization,
            citizen_name='Secret Name', citizen_email='secret@example.com',
            title='Billing error', description='Overcharged on my last bill.',
        )
        captured = {}

        def fake_generate_report(org_name, date_from, date_to, submissions_data):
            captured['data'] = submissions_data
            return make_report_result()

        with patch('apps.ai_insights.services.generate_report', side_effect=fake_generate_report):
            generate_and_store_report(organization, today - timedelta(days=1), today, created_by=org_admin)

        assert captured['data']
        for item in captured['data']:
            assert set(item.keys()) == {'type', 'category', 'title', 'description', 'status'}
            assert 'Secret Name' not in str(item)
            assert 'secret@example.com' not in str(item)


# --- API: AI reports endpoint -------------------------------------------------

class TestAIReportsEndpoint:
    URL = f'{ORG_URL}ai-reports/'

    def test_requires_authentication(self):
        response = APIClient().get(self.URL)
        assert response.status_code == 401

    def test_missing_dates_rejected(self, organization, org_admin):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(self.URL, {})
        assert response.status_code == 400

    def test_invalid_date_range_rejected(self, organization, org_admin):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(self.URL, {'date_from': '2026-02-01', 'date_to': '2026-01-01'})
        assert response.status_code == 400

    def test_returns_503_when_ai_not_configured(self, organization, org_admin, settings):
        settings.ANTHROPIC_API_KEY = ''
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(self.URL, {'date_from': '2026-01-01', 'date_to': '2026-01-31'})
        assert response.status_code == 503

    def test_generates_and_lists_report(self, organization, org_admin, settings):
        settings.ANTHROPIC_API_KEY = 'sk-ant-test-key'
        client = APIClient()
        client.force_authenticate(org_admin)
        with patch('apps.ai_insights.services.generate_report', return_value=make_report_result()):
            create_response = client.post(self.URL, {'date_from': '2026-01-01', 'date_to': '2026-01-31'})
        assert create_response.status_code == 201
        assert create_response.data['summary_english'] == 'Water supply complaints dominated this period.'

        list_response = client.get(self.URL)
        assert list_response.status_code == 200
        assert len(list_response.data) == 1

    def test_staff_without_view_stats_denied(self, organization, org_admin, django_user_model, settings):
        settings.ANTHROPIC_API_KEY = 'sk-ant-test-key'
        staff_user = django_user_model.objects.create_user(
            username='reportstaff', email='reportstaff@example.com', password='Str0ng-pass-123',
        )
        role = StaffRole.objects.create(organization=organization, name='No Stats', privileges=['view_submissions'])
        OrganizationStaff.objects.create(organization=organization, user=staff_user, role=role, status='active')
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.post(self.URL, {'date_from': '2026-01-01', 'date_to': '2026-01-31'})
        assert response.status_code == 403

    def test_reports_scoped_to_own_organization(self, organization, other_organization, org_admin, other_org_admin, settings):
        settings.ANTHROPIC_API_KEY = 'sk-ant-test-key'
        AIReport.objects.create(
            organization=other_organization, date_from='2026-01-01', date_to='2026-01-31',
            submission_count=0, summary_nepali='', summary_english='Other org report',
        )
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.get(self.URL)
        assert response.status_code == 200
        assert all(r['organization'] == organization.id for r in response.data)
