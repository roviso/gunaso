import pytest
from rest_framework.test import APIClient

from apps.organizations.models import Branch, OrganizationStaff, StaffRole
from apps.submissions.models import Submission

pytestmark = pytest.mark.django_db

MAP_FEED_URL = '/api/v1/org/map-feed/'


@pytest.fixture
def located_branch(organization):
    return Branch.objects.create(
        organization=organization, name='Thamel Branch', code='MAPFEED1',
        latitude='27.715300', longitude='85.310000',
    )


@pytest.fixture
def unlocated_branch(organization):
    return Branch.objects.create(organization=organization, name='No Coords Branch', code='MAPFEED2')


class TestMapFeed:
    def test_requires_authentication(self):
        response = APIClient().get(MAP_FEED_URL)
        assert response.status_code == 401

    def test_only_located_active_branches_returned(self, organization, org_admin, located_branch, unlocated_branch):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.get(MAP_FEED_URL)
        assert response.status_code == 200
        ids = {b['id'] for b in response.data['branches']}
        assert located_branch.id in ids
        assert unlocated_branch.id not in ids

    def test_recent_excludes_identity_fields(self, organization, org_admin, located_branch):
        Submission.objects.create(
            reference_number='GUN-2026-00700', organization=organization, branch=located_branch,
            citizen_name='Secret Person', citizen_email='secret@example.com',
            title='Water leak near entrance', description='Leaking for days.',
        )
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.get(MAP_FEED_URL)
        assert response.status_code == 200
        assert len(response.data['recent']) == 1
        entry = response.data['recent'][0]
        assert set(entry.keys()) == {'branch_id', 'reference_number', 'excerpt', 'type', 'status', 'created_at'}
        assert 'Secret Person' not in str(entry)
        assert 'secret@example.com' not in str(entry)

    def test_recent_excludes_submissions_without_branch(self, organization, org_admin, located_branch):
        Submission.objects.create(
            reference_number='GUN-2026-00701', organization=organization, branch=None,
            citizen_name='X', citizen_email='x@example.com',
            title='Org-wide submission', description='No branch attached.',
        )
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.get(MAP_FEED_URL)
        assert response.status_code == 200
        assert response.data['recent'] == []

    def test_requires_view_submissions_privilege(self, organization, org_admin, django_user_model, located_branch):
        staff_user = django_user_model.objects.create_user(
            username='mapstaff', email='mapstaff@example.com', password='Str0ng-pass-123',
        )
        role = StaffRole.objects.create(organization=organization, name='No Access', privileges=['manage_org_profile'])
        OrganizationStaff.objects.create(organization=organization, user=staff_user, role=role, status='active')
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.get(MAP_FEED_URL)
        assert response.status_code == 403

    def test_branch_submission_count_reflected(self, organization, org_admin, located_branch):
        for i in range(3):
            Submission.objects.create(
                reference_number=f'GUN-2026-0080{i}', organization=organization, branch=located_branch,
                citizen_name='X', citizen_email='x@example.com',
                title=f'Issue {i}', description='Some issue description here.',
            )
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.get(MAP_FEED_URL)
        branch_entry = next(b for b in response.data['branches'] if b['id'] == located_branch.id)
        assert branch_entry['submission_count'] == 3
