import pytest
from rest_framework.test import APIClient

from apps.organizations.models import OrganizationStaff, StaffRole

pytestmark = pytest.mark.django_db

ME_URL = '/api/v1/auth/me/'
MY_ACCESS_URL = '/api/v1/organizations/my-access/'


# --- local fixtures -------------------------------------------------------
#
# Build on the shared `organization`/`citizen`/`org_admin` fixtures in
# conftest.py without changing them.

@pytest.fixture
def staff_user(django_user_model):
    return django_user_model.objects.create_user(
        username='staffmember', email='staffmember@ntc.example.com',
        password='Str0ng-pass-123', user_type='citizen',
    )


@pytest.fixture
def support_role(organization):
    return StaffRole.objects.create(
        organization=organization,
        name='Support Agent',
        privileges=['view_submissions', 'manage_submissions'],
    )


def make_staff(organization, user, role, status='active', is_active=True):
    return OrganizationStaff.objects.create(
        organization=organization, user=user, role=role, status=status, is_active=is_active,
    )


# --- GET /organizations/my-access/ ------------------------------------------

class TestMyStaffAccess:
    def test_active_staff_sees_org_role_and_privileges(self, organization, staff_user, support_role):
        make_staff(organization, staff_user, support_role)
        client = APIClient()
        client.force_authenticate(staff_user)

        response = client.get(MY_ACCESS_URL)

        assert response.status_code == 200
        assert response.data['organization_name'] == organization.name
        assert response.data['organization_slug'] == organization.slug
        assert response.data['role_name'] == support_role.name
        assert response.data['privileges'] == support_role.privileges

    def test_invited_but_unaccepted_staff_has_no_active_access(self, organization, staff_user, support_role):
        make_staff(organization, staff_user, support_role, status='invited')
        client = APIClient()
        client.force_authenticate(staff_user)

        response = client.get(MY_ACCESS_URL)

        assert response.status_code == 200
        assert response.data['organization_name'] is None
        assert response.data['organization_slug'] is None
        assert response.data['role_name'] is None
        assert response.data['privileges'] == []

    def test_disabled_staff_has_no_active_access(self, organization, staff_user, support_role):
        make_staff(organization, staff_user, support_role, status='active', is_active=False)
        client = APIClient()
        client.force_authenticate(staff_user)

        response = client.get(MY_ACCESS_URL)

        assert response.status_code == 200
        assert response.data['organization_name'] is None
        assert response.data['role_name'] is None
        assert response.data['privileges'] == []

    def test_plain_citizen_with_no_org_ties_gets_empty_result_not_error(self, citizen):
        client = APIClient()
        client.force_authenticate(citizen)

        response = client.get(MY_ACCESS_URL)

        assert response.status_code == 200
        assert response.data['organization_name'] is None
        assert response.data['organization_slug'] is None
        assert response.data['role_name'] is None
        assert response.data['privileges'] == []

    def test_org_admin_with_no_staff_row_gets_empty_result(self, organization, org_admin):
        client = APIClient()
        client.force_authenticate(org_admin)

        response = client.get(MY_ACCESS_URL)

        assert response.status_code == 200
        assert response.data['organization_name'] is None
        assert response.data['role_name'] is None

    def test_requires_authentication(self):
        response = APIClient().get(MY_ACCESS_URL)
        assert response.status_code == 401

    def test_only_own_membership_is_returned_not_other_staff(
        self, organization, staff_user, support_role, django_user_model,
    ):
        other_staff_user = django_user_model.objects.create_user(
            username='otherstaffer', email='otherstaffer@ntc.example.com',
            password='Str0ng-pass-123', user_type='citizen',
        )
        other_role = StaffRole.objects.create(
            organization=organization, name='Manager', privileges=['manage_staff'],
        )
        make_staff(organization, staff_user, support_role)
        make_staff(organization, other_staff_user, other_role)

        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.get(MY_ACCESS_URL)

        assert response.status_code == 200
        assert response.data['role_name'] == support_role.name
        assert response.data['role_name'] != other_role.name

    def test_org_admin_and_staff_elsewhere_are_not_conflated(
        self, organization, other_organization, org_admin, support_role,
    ):
        """An org_admin of one org who is *also* an active staff member of a
        different org sees both relationships, correctly attributed: the
        managed org via /auth/me/, the staff org via /organizations/my-access/.
        """
        other_org_role = StaffRole.objects.create(
            organization=other_organization, name='Reviewer', privileges=['view_submissions'],
        )
        make_staff(other_organization, org_admin, other_org_role)

        client = APIClient()
        client.force_authenticate(org_admin)

        me_response = client.get(ME_URL)
        assert me_response.status_code == 200
        assert me_response.data['organization_slug'] == organization.slug

        access_response = client.get(MY_ACCESS_URL)
        assert access_response.status_code == 200
        assert access_response.data['organization_slug'] == other_organization.slug
        assert access_response.data['role_name'] == other_org_role.name
        # The two responses must not describe the same organization.
        assert me_response.data['organization_slug'] != access_response.data['organization_slug']


# --- GET /auth/me/ regression: org_admin fields unchanged -------------------

class TestExistingOrgAdminMeFieldsUnchanged:
    def test_org_admin_still_sees_managed_org_via_me(self, organization, org_admin):
        client = APIClient()
        client.force_authenticate(org_admin)

        response = client.get(ME_URL)

        assert response.status_code == 200
        assert response.data['organization_name'] == organization.name
        assert response.data['organization_slug'] == organization.slug

    def test_citizen_sees_null_organization_fields_via_me(self, citizen):
        client = APIClient()
        client.force_authenticate(citizen)

        response = client.get(ME_URL)

        assert response.status_code == 200
        assert response.data['organization_name'] is None
        assert response.data['organization_slug'] is None
