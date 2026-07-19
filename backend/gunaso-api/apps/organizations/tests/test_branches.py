import pytest
from rest_framework.test import APIClient

from apps.organizations.models import Branch, OrganizationStaff, StaffRole

pytestmark = pytest.mark.django_db

ORGS_URL = '/api/v1/organizations/'


# --- local fixtures -------------------------------------------------------

@pytest.fixture
def staff_user(django_user_model):
    return django_user_model.objects.create_user(
        username='branchstaff', email='branchstaff@ntc.example.com',
        password='Str0ng-pass-123', user_type='citizen',
    )


@pytest.fixture
def manage_branches_role(organization):
    return StaffRole.objects.create(
        organization=organization, name='Branch Manager', privileges=['manage_branches'],
    )


@pytest.fixture
def no_access_role(organization):
    return StaffRole.objects.create(
        organization=organization, name='No Access', privileges=['view_stats'],
    )


@pytest.fixture
def branch(organization):
    return Branch.objects.create(
        organization=organization, name='Thamel Branch', code='AAAA1111',
        address='Thamel, Kathmandu', latitude='27.715300', longitude='85.310000',
    )


@pytest.fixture
def inactive_branch(organization):
    return Branch.objects.create(
        organization=organization, name='Closed Branch', code='BBBB2222', is_active=False,
    )


def make_staff(organization, user, role, status='active', is_active=True):
    return OrganizationStaff.objects.create(
        organization=organization, user=user, role=role, status=status, is_active=is_active,
    )


def branches_url(organization):
    return f'{ORGS_URL}{organization.slug}/branches/'


def branch_detail_url(organization, branch_obj):
    return f'{ORGS_URL}{organization.slug}/branches/{branch_obj.id}/'


# --- List/Create ------------------------------------------------------------

class TestBranchesListCreate:
    def test_public_list_shows_only_active_branches(self, organization, branch, inactive_branch):
        response = APIClient().get(branches_url(organization))
        assert response.status_code == 200
        codes = {b['code'] for b in response.data}
        assert branch.code in codes
        assert inactive_branch.code not in codes

    def test_org_admin_list_includes_inactive_branches(self, organization, org_admin, branch, inactive_branch):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.get(branches_url(organization))
        assert response.status_code == 200
        codes = {b['code'] for b in response.data}
        assert {branch.code, inactive_branch.code} <= codes

    def test_anonymous_cannot_create_branch(self, organization):
        response = APIClient().post(branches_url(organization), {'name': 'New Branch'})
        assert response.status_code == 401

    def test_org_admin_can_create_branch(self, organization, org_admin):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(branches_url(organization), {
            'name': 'Pokhara Branch', 'address': 'Lakeside, Pokhara',
            'latitude': '28.209700', 'longitude': '83.985900',
        })
        assert response.status_code == 201
        assert response.data['name'] == 'Pokhara Branch'
        branch_obj = Branch.objects.get(pk=response.data['id'])
        assert branch_obj.organization_id == organization.id
        # code is server-generated, random, and non-empty — never client-supplied
        assert branch_obj.code
        assert len(branch_obj.code) == 8

    def test_client_supplied_code_is_ignored(self, organization, org_admin):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(branches_url(organization), {
            'name': 'Spoofed', 'code': 'HACKED01',
        })
        assert response.status_code == 201
        assert response.data['code'] != 'HACKED01'

    def test_citizen_cannot_create_branch(self, organization, citizen):
        client = APIClient()
        client.force_authenticate(citizen)
        response = client.post(branches_url(organization), {'name': 'Intruder Branch'})
        assert response.status_code == 403

    def test_staff_with_manage_branches_can_create(self, organization, staff_user, manage_branches_role):
        make_staff(organization, staff_user, manage_branches_role)
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.post(branches_url(organization), {'name': 'Staff-created Branch'})
        assert response.status_code == 201

    def test_staff_without_manage_branches_denied(self, organization, staff_user, no_access_role):
        make_staff(organization, staff_user, no_access_role)
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.post(branches_url(organization), {'name': 'Denied Branch'})
        assert response.status_code == 403

    def test_cross_org_admin_cannot_create_branch(self, organization, other_org_admin):
        client = APIClient()
        client.force_authenticate(other_org_admin)
        response = client.post(branches_url(organization), {'name': 'Intruder'})
        assert response.status_code == 403
        assert not Branch.objects.filter(name='Intruder').exists()

    def test_duplicate_name_in_same_org_rejected(self, organization, org_admin, branch):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(branches_url(organization), {'name': 'thamel branch'})
        assert response.status_code == 400
        assert 'name' in response.data['error']['field_errors']

    def test_same_name_allowed_in_different_org(self, organization, other_organization, other_org_admin, branch):
        client = APIClient()
        client.force_authenticate(other_org_admin)
        response = client.post(branches_url(other_organization), {'name': branch.name})
        assert response.status_code == 201


# --- Update/Delete ------------------------------------------------------------

class TestBranchDetail:
    def test_org_admin_can_update_branch(self, organization, org_admin, branch):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.patch(branch_detail_url(organization, branch), {'is_active': False})
        assert response.status_code == 200
        branch.refresh_from_db()
        assert branch.is_active is False

    def test_code_cannot_be_changed_via_patch(self, organization, org_admin, branch):
        original_code = branch.code
        client = APIClient()
        client.force_authenticate(org_admin)
        client.patch(branch_detail_url(organization, branch), {'code': 'NEWCODE1'})
        branch.refresh_from_db()
        assert branch.code == original_code

    def test_org_admin_can_delete_branch(self, organization, org_admin, branch):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.delete(branch_detail_url(organization, branch))
        assert response.status_code == 204
        assert not Branch.objects.filter(pk=branch.id).exists()

    def test_cross_org_admin_cannot_update_branch(self, organization, other_org_admin, branch):
        client = APIClient()
        client.force_authenticate(other_org_admin)
        response = client.patch(branch_detail_url(organization, branch), {'name': 'Hijacked'})
        assert response.status_code in (403, 404)
        branch.refresh_from_db()
        assert branch.name != 'Hijacked'

    def test_cross_org_admin_cannot_delete_branch(self, organization, other_org_admin, branch):
        client = APIClient()
        client.force_authenticate(other_org_admin)
        response = client.delete(branch_detail_url(organization, branch))
        assert response.status_code in (403, 404)
        assert Branch.objects.filter(pk=branch.id).exists()

    def test_staff_without_privilege_cannot_update(self, organization, staff_user, no_access_role, branch):
        make_staff(organization, staff_user, no_access_role)
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.patch(branch_detail_url(organization, branch), {'name': 'Renamed'})
        assert response.status_code == 403

    def test_unauthenticated_cannot_delete(self, organization, branch):
        response = APIClient().delete(branch_detail_url(organization, branch))
        assert response.status_code == 401
        assert Branch.objects.filter(pk=branch.id).exists()


# --- Submission ↔ branch traceability ----------------------------------------

class TestSubmissionBranchTraceability:
    SUBMISSIONS_URL = '/api/v1/submissions/'

    def _payload(self, organization, branch_code=''):
        payload = {
            'organization': organization.id,
            'type': 'complaint',
            'title': 'Water leakage near office',
            'description': 'There has been a persistent water leak for two weeks now.',
            'is_anonymous': True,
        }
        if branch_code:
            payload['branch_code'] = branch_code
        return payload

    def test_submission_via_branch_qr_records_branch(self, organization, branch):
        client = APIClient()
        response = client.post(self.SUBMISSIONS_URL, self._payload(organization, branch.code))
        assert response.status_code == 201
        assert response.data['branch_name'] == branch.name

        from apps.submissions.models import Submission
        submission = Submission.objects.get(reference_number=response.data['reference_number'])
        assert submission.branch_id == branch.id

    def test_submission_without_branch_code_has_no_branch(self, organization):
        client = APIClient()
        response = client.post(self.SUBMISSIONS_URL, self._payload(organization))
        assert response.status_code == 201
        assert response.data['branch_name'] is None

    def test_branch_code_from_other_org_rejected(self, organization, other_organization):
        foreign_branch = Branch.objects.create(
            organization=other_organization, name='Foreign Branch', code='FOREIGN1',
        )
        client = APIClient()
        response = client.post(self.SUBMISSIONS_URL, self._payload(organization, foreign_branch.code))
        assert response.status_code == 400
        assert 'branch_code' in response.data['error']['field_errors']

    def test_inactive_branch_code_rejected(self, organization, inactive_branch):
        client = APIClient()
        response = client.post(self.SUBMISSIONS_URL, self._payload(organization, inactive_branch.code))
        assert response.status_code == 400
        assert 'branch_code' in response.data['error']['field_errors']

    def test_org_dashboard_can_filter_submissions_by_branch(self, organization, org_admin, branch):
        client = APIClient()
        client.post(self.SUBMISSIONS_URL, self._payload(organization, branch.code))
        client.post(self.SUBMISSIONS_URL, self._payload(organization))

        client.force_authenticate(org_admin)
        response = client.get(f'{ORGS_URL}{organization.slug}/submissions/', {'branch': branch.id})
        assert response.status_code == 200
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['branch_name'] == branch.name

    def test_org_stats_includes_per_branch_breakdown(self, organization, org_admin, branch):
        client = APIClient()
        client.post(self.SUBMISSIONS_URL, self._payload(organization, branch.code))
        client.post(self.SUBMISSIONS_URL, self._payload(organization, branch.code))

        client.force_authenticate(org_admin)
        response = client.get(f'{ORGS_URL}{organization.slug}/stats/')
        assert response.status_code == 200
        by_branch = {row['id']: row['count'] for row in response.data['by_branch']}
        assert by_branch.get(branch.id) == 2


# --- Branch QR code ------------------------------------------------------

class TestBranchQRCode:
    def qr_url(self, organization, branch_obj):
        return f'{ORGS_URL}{organization.slug}/branches/{branch_obj.id}/qrcode/'

    def test_public_can_fetch_branch_qr_png(self, organization, branch):
        response = APIClient().get(self.qr_url(organization, branch))
        assert response.status_code == 200
        assert response['Content-Type'] == 'image/png'

    def test_base64_format_encodes_branch_code_in_url(self, organization, branch):
        import json
        response = APIClient().get(self.qr_url(organization, branch), {'format': 'base64'})
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['branch_name'] == branch.name
        assert data['url'].endswith(f'/submit/{organization.slug}?branch={branch.code}')

    def test_inactive_branch_qr_returns_404(self, organization, inactive_branch):
        response = APIClient().get(self.qr_url(organization, inactive_branch))
        assert response.status_code == 404

    def test_branch_from_other_org_returns_404(self, other_organization, branch):
        response = APIClient().get(self.qr_url(other_organization, branch))
        assert response.status_code == 404
