import io

import pytest
from rest_framework.test import APIClient

from apps.submissions.models import InvalidStatusTransitionError, Submission
from apps.submissions.services import transition_status

pytestmark = pytest.mark.django_db

SUBMISSIONS_URL = '/api/v1/submissions/'

VALID_PAYLOAD = {
    'type': 'complaint',
    'category': 'Network Issue',
    'title': 'Internet keeps disconnecting',
    'description': 'The connection drops every ten minutes throughout the day.',
    'priority': 'high',
    'submitter_name': 'Gita Thapa',
    'submitter_email': 'gita@example.com',
}


class TestSubmissionCreate:
    def test_anonymous_visitor_can_submit(self, organization):
        response = APIClient().post(SUBMISSIONS_URL, {
            **VALID_PAYLOAD, 'organization': organization.id,
        })
        assert response.status_code == 201
        assert response.data['reference_number'].startswith('GUN-')
        assert response.data['status'] == 'submitted'
        assert response.data['organization_name'] == organization.name
        assert response.data['category'] == 'Network Issue'

    def test_anonymous_flag_allows_missing_identity(self, organization):
        payload = {
            'organization': organization.id,
            'type': 'complaint',
            'title': 'Anonymous corruption report',
            'description': 'Details of the irregularities I have witnessed recently.',
            'is_anonymous': True,
        }
        response = APIClient().post(SUBMISSIONS_URL, payload)
        assert response.status_code == 201
        assert response.data['submitter_name'] == 'Anonymous'

    def test_identity_required_when_not_anonymous(self, organization):
        payload = {
            'organization': organization.id,
            'title': 'Missing contact info',
            'description': 'This should fail because no name or email was given.',
        }
        response = APIClient().post(SUBMISSIONS_URL, payload)
        assert response.status_code == 400
        assert 'submitter_name' in response.data['error']['field_errors']

    def test_authenticated_citizen_is_linked(self, organization, citizen):
        client = APIClient()
        client.force_authenticate(citizen)
        response = client.post(SUBMISSIONS_URL, {
            **VALID_PAYLOAD, 'organization': organization.id,
        })
        assert response.status_code == 201
        submission = Submission.objects.get(reference_number=response.data['reference_number'])
        assert submission.citizen == citizen

    def test_attachment_with_disallowed_extension_rejected(self, organization):
        bad_file = io.BytesIO(b'MZ executable content')
        bad_file.name = 'malware.exe'
        response = APIClient().post(
            SUBMISSIONS_URL,
            {**VALID_PAYLOAD, 'organization': organization.id, 'attachment': bad_file},
            format='multipart',
        )
        assert response.status_code == 400

    def test_attachment_with_mismatched_content_rejected(self, organization):
        fake_png = io.BytesIO(b'this is definitely not a png')
        fake_png.name = 'evidence.png'
        response = APIClient().post(
            SUBMISSIONS_URL,
            {**VALID_PAYLOAD, 'organization': organization.id, 'attachment': fake_png},
            format='multipart',
        )
        assert response.status_code == 400


class TestTracking:
    def test_public_tracking_never_exposes_contact_details(self, submission):
        response = APIClient().get(f'{SUBMISSIONS_URL}track/{submission.reference_number}/')
        assert response.status_code == 200
        assert response.data['title'] == submission.title
        assert 'submitter_email' not in response.data
        assert 'submitter_phone' not in response.data

    def test_tracking_is_case_insensitive(self, submission):
        ref = submission.reference_number.lower()
        assert APIClient().get(f'{SUBMISSIONS_URL}track/{ref}/').status_code == 200

    def test_unknown_reference_returns_404(self):
        response = APIClient().get(f'{SUBMISSIONS_URL}track/GUN-2026-99999/')
        assert response.status_code == 404


class TestAnonymityRedaction:
    def test_org_admin_cannot_see_anonymous_identity(self, anonymous_submission, org_admin):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.get(f'{SUBMISSIONS_URL}{anonymous_submission.reference_number}/')
        assert response.status_code == 200
        assert response.data['submitter_name'] == 'Anonymous'
        assert response.data['submitter_email'] is None

    def test_platform_staff_can_see_identity_of_named_submission(self, submission, platform_staff):
        client = APIClient()
        client.force_authenticate(platform_staff)
        response = client.get(f'{SUBMISSIONS_URL}{submission.reference_number}/')
        assert response.data['submitter_email'] == 'ram@example.com'

    def test_unrelated_citizen_cannot_open_submission_detail(self, submission, django_user_model):
        stranger = django_user_model.objects.create_user(
            username='stranger', email='stranger@example.com', password='Str0ng-pass-123',
        )
        client = APIClient()
        client.force_authenticate(stranger)
        response = client.get(f'{SUBMISSIONS_URL}{submission.reference_number}/')
        assert response.status_code == 403


class TestStatusTransitions:
    def test_valid_transition_creates_audit_record(self, submission, org_admin):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.patch(
            f'{SUBMISSIONS_URL}{submission.reference_number}/status/',
            {'status': 'acknowledged', 'note': 'We are on it.'},
        )
        assert response.status_code == 200
        assert response.data['status'] == 'acknowledged'
        assert response.data['timeline'][-1]['note'] == 'We are on it.'

    def test_invalid_transition_rejected_with_409(self, submission, org_admin):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.patch(
            f'{SUBMISSIONS_URL}{submission.reference_number}/status/',
            {'status': 'closed'},
        )
        assert response.status_code == 409

    def test_other_org_admin_cannot_update_status(self, submission, other_org_admin):
        client = APIClient()
        client.force_authenticate(other_org_admin)
        response = client.patch(
            f'{SUBMISSIONS_URL}{submission.reference_number}/status/',
            {'status': 'acknowledged'},
        )
        assert response.status_code == 403

    def test_full_lifecycle_and_terminal_state(self, submission, org_admin):
        for step in ['acknowledged', 'in_review', 'resolved', 'closed']:
            transition_status(submission, step, changed_by=org_admin)
        assert submission.resolved_at is not None
        with pytest.raises(InvalidStatusTransitionError):
            transition_status(submission, 'in_review', changed_by=org_admin)


class TestMySubmissions:
    def test_citizen_sees_only_own_submissions(self, submission, anonymous_submission, citizen):
        client = APIClient()
        client.force_authenticate(citizen)
        response = client.get(f'{SUBMISSIONS_URL}my/')
        assert response.status_code == 200
        refs = [s['reference_number'] for s in response.data['results']]
        assert submission.reference_number in refs
        assert anonymous_submission.reference_number not in refs


class TestOrgAdminEndpoints:
    def test_org_submissions_scoped_to_own_org(
        self, submission, org_admin, other_organization, other_org_admin
    ):
        Submission.objects.create(
            reference_number='GUN-2026-00099',
            organization=other_organization,
            citizen_name='Someone Else',
            citizen_email='someone@example.com',
            title='Other org complaint',
            description='A complaint that belongs to a different organization.',
        )
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.get('/api/v1/org/submissions/')
        refs = [s['reference_number'] for s in response.data['results']]
        assert submission.reference_number in refs
        assert 'GUN-2026-00099' not in refs

    def test_org_stats_shape_matches_dashboard(self, submission, org_admin):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.get('/api/v1/org/stats/')
        assert response.status_code == 200
        for key in [
            'total', 'pending', 'in_review', 'escalated', 'resolved_this_month',
            'avg_resolution_days', 'by_status', 'by_type', 'by_priority',
            'unassigned_count', 'staff_count', 'trend',
        ]:
            assert key in response.data
