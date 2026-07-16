import pytest
from rest_framework.test import APIClient

from apps.organizations.models import OrganizationStaff, StaffRole
from apps.organizations.privileges import STAFF_PRIVILEGE_KEYS

pytestmark = pytest.mark.django_db

ORGS_URL = '/api/v1/organizations/'


# --- local fixtures -------------------------------------------------------

@pytest.fixture
def staff_user(django_user_model):
    return django_user_model.objects.create_user(
        username='staffmember', email='staffmember@ntc.example.com',
        password='Str0ng-pass-123', user_type='citizen',
    )


@pytest.fixture
def manage_roles_role(organization):
    return StaffRole.objects.create(
        organization=organization, name='Role Manager', privileges=['manage_roles'],
    )


@pytest.fixture
def no_access_role(organization):
    return StaffRole.objects.create(
        organization=organization, name='No Access', privileges=['view_stats'],
    )


def make_staff(organization, user, role, status='active', is_active=True):
    return OrganizationStaff.objects.create(
        organization=organization, user=user, role=role, status=status, is_active=is_active,
    )


def roles_url(organization):
    return f'{ORGS_URL}{organization.slug}/roles/'


def role_detail_url(organization, role):
    return f'{ORGS_URL}{organization.slug}/roles/{role.id}/'


# --- Privilege catalog endpoint ---------------------------------------------

class TestPrivilegeCatalog:
    def test_requires_authentication(self):
        response = APIClient().get(f'{ORGS_URL}privileges/')
        assert response.status_code == 401

    def test_authenticated_user_gets_full_catalog(self, citizen):
        client = APIClient()
        client.force_authenticate(citizen)
        response = client.get(f'{ORGS_URL}privileges/')
        assert response.status_code == 200
        keys = {entry['key'] for entry in response.data}
        assert keys == STAFF_PRIVILEGE_KEYS
        for entry in response.data:
            assert set(entry.keys()) == {'key', 'label', 'group'}


# --- List/Create roles -------------------------------------------------------

class TestRolesListCreate:
    def test_requires_authentication(self, organization):
        response = APIClient().get(roles_url(organization))
        assert response.status_code == 401

    def test_org_admin_can_list_roles(self, organization, org_admin):
        StaffRole.objects.create(organization=organization, name='Agent', privileges=['view_submissions'])
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.get(roles_url(organization))
        assert response.status_code == 200
        names = [r['name'] for r in response.data]
        assert 'Agent' in names

    def test_list_includes_staff_count(self, organization, org_admin, staff_user):
        role = StaffRole.objects.create(organization=organization, name='Agent', privileges=['view_submissions'])
        make_staff(organization, staff_user, role)
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.get(roles_url(organization))
        assert response.status_code == 200
        entry = next(r for r in response.data if r['id'] == role.id)
        assert entry['staff_count'] == 1

    def test_non_admin_non_staff_denied(self, organization, citizen):
        client = APIClient()
        client.force_authenticate(citizen)
        response = client.get(roles_url(organization))
        assert response.status_code == 403

    def test_staff_with_manage_roles_privilege_can_list(self, organization, staff_user, manage_roles_role):
        make_staff(organization, staff_user, manage_roles_role)
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.get(roles_url(organization))
        assert response.status_code == 200

    def test_staff_without_manage_roles_privilege_denied(self, organization, staff_user, no_access_role):
        make_staff(organization, staff_user, no_access_role)
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.get(roles_url(organization))
        assert response.status_code == 403

    def test_org_admin_can_create_role(self, organization, org_admin):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(roles_url(organization), {
            'name': 'Support Agent',
            'privileges': ['view_submissions', 'manage_submissions'],
        }, format='json')
        assert response.status_code == 201
        assert response.data['name'] == 'Support Agent'
        assert response.data['staff_count'] == 0
        role = StaffRole.objects.get(pk=response.data['id'])
        assert role.organization_id == organization.id

    def test_staff_with_privilege_can_create_role(self, organization, staff_user, manage_roles_role):
        make_staff(organization, staff_user, manage_roles_role)
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.post(roles_url(organization), {
            'name': 'Auditor', 'privileges': ['view_stats'],
        }, format='json')
        assert response.status_code == 201

    def test_duplicate_name_rejected_with_field_errors(self, organization, org_admin):
        StaffRole.objects.create(organization=organization, name='Agent', privileges=[])
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(roles_url(organization), {
            'name': 'Agent', 'privileges': [],
        }, format='json')
        assert response.status_code == 400
        assert 'name' in response.data['error']['field_errors']

    def test_duplicate_name_case_insensitive(self, organization, org_admin):
        StaffRole.objects.create(organization=organization, name='Agent', privileges=[])
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(roles_url(organization), {
            'name': 'AGENT', 'privileges': [],
        }, format='json')
        assert response.status_code == 400

    def test_same_name_allowed_in_different_org(self, organization, other_organization, org_admin, other_org_admin):
        StaffRole.objects.create(organization=organization, name='Agent', privileges=[])
        client = APIClient()
        client.force_authenticate(other_org_admin)
        response = client.post(roles_url(other_organization), {
            'name': 'Agent', 'privileges': [],
        }, format='json')
        assert response.status_code == 201

    def test_unknown_privilege_key_rejected(self, organization, org_admin):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(roles_url(organization), {
            'name': 'Sneaky Role', 'privileges': ['view_submissions', 'delete_everything'],
        }, format='json')
        assert response.status_code == 400
        assert 'privileges' in response.data['error']['field_errors']
        assert not StaffRole.objects.filter(name='Sneaky Role').exists()

    def test_cross_org_admin_cannot_list_other_org_roles(self, organization, other_org_admin):
        StaffRole.objects.create(organization=organization, name='Agent', privileges=[])
        client = APIClient()
        client.force_authenticate(other_org_admin)
        response = client.get(roles_url(organization))
        assert response.status_code == 403

    def test_cross_org_admin_cannot_create_role_for_other_org(self, organization, other_org_admin):
        client = APIClient()
        client.force_authenticate(other_org_admin)
        response = client.post(roles_url(organization), {
            'name': 'Intruder', 'privileges': [],
        }, format='json')
        assert response.status_code == 403
        assert not StaffRole.objects.filter(name='Intruder').exists()


# --- Update/Delete a role ----------------------------------------------------

class TestRoleDetail:
    def test_org_admin_can_update_role_privileges(self, organization, org_admin):
        role = StaffRole.objects.create(organization=organization, name='Agent', privileges=['view_submissions'])
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.patch(role_detail_url(organization, role), {
            'privileges': ['view_submissions', 'manage_submissions'],
        }, format='json')
        assert response.status_code == 200
        role.refresh_from_db()
        assert role.privileges == ['view_submissions', 'manage_submissions']

    def test_update_unknown_privilege_rejected(self, organization, org_admin):
        role = StaffRole.objects.create(organization=organization, name='Agent', privileges=['view_submissions'])
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.patch(role_detail_url(organization, role), {
            'privileges': ['not_a_real_privilege'],
        }, format='json')
        assert response.status_code == 400
        role.refresh_from_db()
        assert role.privileges == ['view_submissions']

    def test_update_to_duplicate_name_rejected(self, organization, org_admin):
        StaffRole.objects.create(organization=organization, name='Existing', privileges=[])
        role = StaffRole.objects.create(organization=organization, name='Agent', privileges=[])
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.patch(role_detail_url(organization, role), {
            'name': 'Existing',
        }, format='json')
        assert response.status_code == 400

    def test_rename_to_same_name_allowed(self, organization, org_admin):
        role = StaffRole.objects.create(organization=organization, name='Agent', privileges=[])
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.patch(role_detail_url(organization, role), {
            'name': 'Agent',
        }, format='json')
        assert response.status_code == 200

    def test_delete_unused_role_succeeds(self, organization, org_admin):
        role = StaffRole.objects.create(organization=organization, name='Unused', privileges=[])
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.delete(role_detail_url(organization, role))
        assert response.status_code == 204
        assert not StaffRole.objects.filter(pk=role.id).exists()

    def test_delete_role_in_use_returns_409_not_500(self, organization, org_admin, staff_user):
        role = StaffRole.objects.create(organization=organization, name='In Use', privileges=[])
        make_staff(organization, staff_user, role)
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.delete(role_detail_url(organization, role))
        assert response.status_code == 409
        assert StaffRole.objects.filter(pk=role.id).exists()

    def test_cross_org_admin_cannot_update_role(self, organization, other_org_admin):
        role = StaffRole.objects.create(organization=organization, name='Agent', privileges=[])
        client = APIClient()
        client.force_authenticate(other_org_admin)
        response = client.patch(role_detail_url(organization, role), {'name': 'Hijacked'}, format='json')
        assert response.status_code in (403, 404)
        role.refresh_from_db()
        assert role.name == 'Agent'

    def test_cross_org_admin_cannot_delete_role(self, organization, other_org_admin):
        role = StaffRole.objects.create(organization=organization, name='Agent', privileges=[])
        client = APIClient()
        client.force_authenticate(other_org_admin)
        response = client.delete(role_detail_url(organization, role))
        assert response.status_code in (403, 404)
        assert StaffRole.objects.filter(pk=role.id).exists()

    def test_staff_without_manage_roles_privilege_cannot_update(self, organization, staff_user, no_access_role):
        make_staff(organization, staff_user, no_access_role)
        role = StaffRole.objects.create(organization=organization, name='Agent', privileges=[])
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.patch(role_detail_url(organization, role), {'name': 'Renamed'}, format='json')
        assert response.status_code == 403

    def test_staff_without_manage_roles_privilege_cannot_delete(self, organization, staff_user, no_access_role):
        make_staff(organization, staff_user, no_access_role)
        role = StaffRole.objects.create(organization=organization, name='Agent', privileges=[])
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.delete(role_detail_url(organization, role))
        assert response.status_code == 403
        assert StaffRole.objects.filter(pk=role.id).exists()


# --- OrganizationStaffView.post: role resolved against org's StaffRole set --

class TestStaffCreationResolvesRoleByOrg:
    def test_create_staff_with_valid_role_id(self, organization, org_admin, citizen):
        role = StaffRole.objects.create(organization=organization, name='Agent', privileges=['view_submissions'])
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(f'{ORGS_URL}{organization.slug}/staff/', {
            'user_email': citizen.email, 'role': role.id,
        })
        assert response.status_code == 201
        assert response.data['role'] == role.id
        assert response.data['role_name'] == 'Agent'

    def test_create_staff_missing_role_rejected(self, organization, org_admin, citizen):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(f'{ORGS_URL}{organization.slug}/staff/', {
            'user_email': citizen.email,
        })
        assert response.status_code == 400
        assert 'role' in response.data['error']['field_errors']

    def test_create_staff_with_role_from_other_org_rejected(self, organization, other_organization, org_admin, citizen):
        foreign_role = StaffRole.objects.create(
            organization=other_organization, name='Foreign Agent', privileges=['view_submissions'],
        )
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(f'{ORGS_URL}{organization.slug}/staff/', {
            'user_email': citizen.email, 'role': foreign_role.id,
        })
        assert response.status_code == 400
        assert 'role' in response.data['error']['field_errors']
        assert not OrganizationStaff.objects.filter(organization=organization, user=citizen).exists()

    def test_patch_staff_role_scoped_to_org(self, organization, other_organization, org_admin, staff_user):
        role = StaffRole.objects.create(organization=organization, name='Agent', privileges=[])
        staff = make_staff(organization, staff_user, role)
        foreign_role = StaffRole.objects.create(organization=other_organization, name='Foreign', privileges=[])
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.patch(f'{ORGS_URL}{organization.slug}/staff/{staff.id}/', {
            'role': foreign_role.id,
        })
        assert response.status_code == 400
