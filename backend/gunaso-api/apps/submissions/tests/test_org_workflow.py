"""Organization-side case handling: staff access to details/notes, contact
visibility, SLA/overdue flags, CSV export and the branch hotspot map."""
import csv
import io
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.organizations.models import Branch, OrganizationStaff, StaffRole
from apps.submissions.models import Submission

pytestmark = pytest.mark.django_db

SUBMISSIONS_URL = '/api/v1/submissions/'
ORG_LIST_URL = '/api/v1/org/submissions/'
EXPORT_URL = '/api/v1/org/submissions/export/'
MAP_FEED_URL = '/api/v1/org/map-feed/'


def make_staff_member(django_user_model, organization, username, privileges):
    user = django_user_model.objects.create_user(
        username=username, email=f'{username}@ntc.example.com', password='Str0ng-pass-123',
    )
    role = StaffRole.objects.create(organization=organization, name=f'Role {username}', privileges=privileges)
    OrganizationStaff.objects.create(organization=organization, user=user, role=role, status='active')
    return user


@pytest.fixture
def handler(django_user_model, organization):
    return make_staff_member(django_user_model, organization, 'handler', ['view_submissions', 'manage_submissions'])


@pytest.fixture
def viewer(django_user_model, organization):
    return make_staff_member(django_user_model, organization, 'viewer', ['view_submissions'])


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def age(submission, **delta):
    Submission.objects.filter(pk=submission.pk).update(created_at=timezone.now() - timedelta(**delta))
    submission.refresh_from_db()


class TestStaffCaseAccess:
    def test_staff_with_view_privilege_can_open_detail(self, submission, viewer):
        response = client_for(viewer).get(f'{SUBMISSIONS_URL}{submission.reference_number}/')
        assert response.status_code == 200

    def test_staff_of_other_org_cannot_open_detail(self, django_user_model, other_organization, submission):
        outsider = make_staff_member(django_user_model, other_organization, 'outsider', ['view_submissions'])
        response = client_for(outsider).get(f'{SUBMISSIONS_URL}{submission.reference_number}/')
        assert response.status_code == 403

    def test_staff_without_privilege_cannot_open_detail(self, django_user_model, organization, submission):
        user = make_staff_member(django_user_model, organization, 'noprivs', ['view_stats'])
        assert client_for(user).get(f'{SUBMISSIONS_URL}{submission.reference_number}/').status_code == 403

    def test_handler_can_reply(self, submission, handler):
        response = client_for(handler).post(
            f'{SUBMISSIONS_URL}{submission.reference_number}/updates/', {'note': 'Visiting tomorrow'},
        )
        assert response.status_code == 201
        assert response.data['kind'] == 'note'

    def test_view_only_staff_cannot_reply(self, submission, viewer):
        response = client_for(viewer).post(
            f'{SUBMISSIONS_URL}{submission.reference_number}/updates/', {'note': 'Visiting tomorrow'},
        )
        assert response.status_code == 403

    def test_view_only_staff_can_read_updates_including_internal(self, submission, viewer, org_admin):
        from apps.submissions.services import add_staff_note
        add_staff_note(submission, 'internal thing', author=org_admin, internal=True)
        response = client_for(viewer).get(f'{SUBMISSIONS_URL}{submission.reference_number}/updates/')
        assert response.status_code == 200
        assert 'internal thing' in [u['note'] for u in response.data]


class TestContactVisibility:
    def test_handler_sees_contact_details(self, submission, handler):
        data = client_for(handler).get(f'{SUBMISSIONS_URL}{submission.reference_number}/').data
        assert data['submitter_email'] == 'ram@example.com'
        assert data['submitter_phone'] == '9801234567'

    def test_view_only_staff_does_not_see_contact_details(self, submission, viewer):
        data = client_for(viewer).get(f'{SUBMISSIONS_URL}{submission.reference_number}/').data
        assert data['submitter_name'] == 'Ram Sharma'
        assert data['submitter_email'] is None
        assert data['submitter_phone'] is None

    def test_handler_never_sees_anonymous_identity(self, organization, handler):
        Submission.objects.create(
            reference_number='GUN-2026-00333', organization=organization, is_anonymous=True,
            citizen_name='Hidden Person', citizen_email='hidden@example.com',
            title='Anonymous report', description='Something that needs anonymity to report.',
        )
        data = client_for(handler).get(f'{SUBMISSIONS_URL}GUN-2026-00333/').data
        assert data['submitter_name'] == 'Anonymous'
        assert data['submitter_email'] is None


class TestOverdue:
    def test_unacknowledged_past_response_target_is_overdue(self, submission, org_admin, settings):
        settings.SLA_RESPONSE_HOURS = 72
        age(submission, hours=80)
        data = client_for(org_admin).get(f'{SUBMISSIONS_URL}{submission.reference_number}/').data
        assert data['is_overdue'] is True

    def test_fresh_submission_is_not_overdue(self, submission, org_admin):
        data = client_for(org_admin).get(f'{SUBMISSIONS_URL}{submission.reference_number}/').data
        assert data['is_overdue'] is False

    def test_acknowledged_is_only_overdue_after_resolution_target(self, submission, org_admin, settings):
        settings.SLA_RESOLUTION_DAYS = 30
        Submission.objects.filter(pk=submission.pk).update(status='acknowledged')
        age(submission, days=5)
        client = client_for(org_admin)
        assert client.get(f'{SUBMISSIONS_URL}{submission.reference_number}/').data['is_overdue'] is False
        age(submission, days=31)
        assert client.get(f'{SUBMISSIONS_URL}{submission.reference_number}/').data['is_overdue'] is True

    def test_resolved_is_never_overdue(self, submission, org_admin):
        Submission.objects.filter(pk=submission.pk).update(status='resolved')
        age(submission, days=365)
        data = client_for(org_admin).get(f'{SUBMISSIONS_URL}{submission.reference_number}/').data
        assert data['is_overdue'] is False

    def test_overdue_filter_and_stats(self, submission, anonymous_submission, org_admin):
        age(submission, days=10)
        client = client_for(org_admin)
        refs = [s['reference_number'] for s in client.get(ORG_LIST_URL, {'overdue': 'true'}).data['results']]
        assert refs == [submission.reference_number]
        stats = client.get('/api/v1/org/stats/').data
        assert stats['overdue_count'] == 1
        assert stats['sla']['response_hours'] > 0


class TestExport:
    def _rows(self, response):
        text = b''.join(response).decode('utf-8-sig') if hasattr(response, 'streaming_content') \
            else response.content.decode('utf-8-sig')
        return list(csv.reader(io.StringIO(text)))

    def test_requires_view_privilege(self, django_user_model, organization, submission):
        user = make_staff_member(django_user_model, organization, 'statsonly', ['view_stats'])
        assert client_for(user).get(EXPORT_URL).status_code == 403

    def test_user_without_org_gets_404(self, citizen):
        assert client_for(citizen).get(EXPORT_URL).status_code == 404

    def test_anonymous_request_is_401(self):
        assert APIClient().get(EXPORT_URL).status_code == 401

    def test_export_redacts_anonymous_and_neutralizes_formulas(self, organization, org_admin, submission):
        Submission.objects.create(
            reference_number='GUN-2026-00444', organization=organization, is_anonymous=True,
            citizen_name='Hidden Person', citizen_email='hidden@example.com',
            title='=HYPERLINK("http://evil")', description='@SUM(A1:A2) formula attempt here.',
        )
        response = client_for(org_admin).get(EXPORT_URL)
        assert response.status_code == 200
        assert response['Content-Type'].startswith('text/csv')
        rows = self._rows(response)
        header, body = rows[0], rows[1:]
        by_ref = {r[0]: dict(zip(header, r)) for r in body}

        anon = by_ref['GUN-2026-00444']
        assert anon['Submitter'] == 'Anonymous'
        assert anon['Email'] == ''
        assert 'hidden' not in ','.join(anon.values())
        assert anon['Title'].startswith("'=")
        assert anon['Description'].startswith("'@")

        named = by_ref[submission.reference_number]
        assert named['Email'] == 'ram@example.com'

    def test_view_only_staff_export_has_no_contact_details(self, submission, viewer):
        rows = self._rows(client_for(viewer).get(EXPORT_URL))
        header = rows[0]
        row = dict(zip(header, rows[1]))
        assert row['Submitter'] == 'Ram Sharma'
        assert row['Email'] == ''
        assert row['Phone'] == ''

    def test_export_respects_filters(self, submission, anonymous_submission, org_admin):
        Submission.objects.filter(pk=submission.pk).update(status='resolved')
        rows = self._rows(client_for(org_admin).get(EXPORT_URL, {'status': 'resolved'}))
        assert [r[0] for r in rows[1:]] == [submission.reference_number]


class TestMapFeedHotspots:
    @pytest.fixture
    def branch(self, organization):
        return Branch.objects.create(
            organization=organization, name='Baneshwor', code='HOTSPOT1',
            latitude='27.690000', longitude='85.340000',
        )

    def test_per_branch_workload(self, organization, org_admin, branch):
        for i, (status, typ) in enumerate([
            ('submitted', 'complaint'), ('in_review', 'complaint'), ('resolved', 'feedback'),
        ]):
            Submission.objects.create(
                reference_number=f'GUN-2026-0080{i}', organization=organization, branch=branch,
                status=status, submission_type=typ, title=f'Issue {i}', description='x' * 30,
            )
        Submission.objects.create(
            reference_number='GUN-2026-00810', organization=organization,
            title='No branch', description='x' * 30,
        )
        data = client_for(org_admin).get(MAP_FEED_URL).data
        b = data['branches'][0]
        assert b['submission_count'] == 3
        assert b['open_count'] == 2
        assert b['resolved_count'] == 1
        assert b['by_type'] == {'complaint': 2, 'feedback': 1, 'suggestion': 0}
        assert data['unlinked_count'] == 1

    def test_window_filter(self, organization, org_admin, branch):
        old = Submission.objects.create(
            reference_number='GUN-2026-00820', organization=organization, branch=branch,
            title='Old one', description='x' * 30,
        )
        age(old, days=45)
        Submission.objects.create(
            reference_number='GUN-2026-00821', organization=organization, branch=branch,
            title='New one', description='x' * 30,
        )
        client = client_for(org_admin)
        assert client.get(MAP_FEED_URL, {'days': '30'}).data['branches'][0]['submission_count'] == 1
        assert client.get(MAP_FEED_URL, {'days': '90'}).data['branches'][0]['submission_count'] == 2
        assert client.get(MAP_FEED_URL).data['branches'][0]['submission_count'] == 2
        assert [r['reference_number'] for r in client.get(MAP_FEED_URL, {'days': '30'}).data['recent']] == [
            'GUN-2026-00821'
        ]

    def test_overdue_per_branch(self, organization, org_admin, branch):
        s = Submission.objects.create(
            reference_number='GUN-2026-00830', organization=organization, branch=branch,
            title='Waiting', description='x' * 30,
        )
        age(s, days=10)
        data = client_for(org_admin).get(MAP_FEED_URL).data
        assert data['branches'][0]['overdue_count'] == 1


class TestAssignment:
    def test_null_staff_id_unassigns(self, organization, submission, org_admin, handler):
        staff = OrganizationStaff.objects.get(user=handler)
        client = client_for(org_admin)
        url = f'{SUBMISSIONS_URL}{submission.reference_number}/assign/'
        assert client.patch(url, {'staff_id': staff.id}, format='json').data['assigned_to']['id'] == staff.id
        response = client.patch(url, {'staff_id': None}, format='json')
        assert response.status_code == 200
        assert response.data['assigned_to'] is None

    def test_missing_staff_id_is_rejected(self, submission, org_admin):
        response = client_for(org_admin).patch(f'{SUBMISSIONS_URL}{submission.reference_number}/assign/', {})
        assert response.status_code == 400

    def test_unassign_requires_privilege(self, submission, viewer):
        response = client_for(viewer).patch(
            f'{SUBMISSIONS_URL}{submission.reference_number}/assign/', {'staff_id': None}, format='json',
        )
        assert response.status_code == 403
