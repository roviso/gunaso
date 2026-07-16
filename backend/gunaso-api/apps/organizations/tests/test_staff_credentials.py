import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.organizations.models import OrganizationStaff, StaffRole

pytestmark = pytest.mark.django_db

ORGS_URL = '/api/v1/organizations/'


@pytest.fixture
def agent_role(organization):
    return StaffRole.objects.create(
        organization=organization, name='Agent', privileges=['view_submissions'],
    )


def staff_url(organization):
    return f'{ORGS_URL}{organization.slug}/staff/'


def _payload(role, **overrides):
    payload = {
        'mode': 'credentials',
        'username': 'newstaff01',
        'password': 'Str0ng-pass-456',
        'email': 'newstaff@ntc.example.com',
        'role': role.id,
    }
    payload.update(overrides)
    return payload


class TestCreateStaffWithCredentials:
    def test_creates_active_user_forcing_password_change(self, organization, org_admin, agent_role):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(staff_url(organization), _payload(agent_role))
        assert response.status_code == 201
        assert response.data['status'] == 'active'
        assert response.data['invited'] is False
        assert response.data['invite_link'] is None

        user = User.objects.get(username='newstaff01')
        assert user.is_active is True
        assert user.has_usable_password()
        assert user.must_change_password is True
        assert user.email_verified is False

        staff = OrganizationStaff.objects.get(organization=organization, user=user)
        assert staff.status == 'active'
        assert staff.role_id == agent_role.id

    def test_new_staff_can_log_in_immediately_with_username(self, organization, org_admin, agent_role):
        client = APIClient()
        client.force_authenticate(org_admin)
        client.post(staff_url(organization), _payload(agent_role))

        login_client = APIClient()
        response = login_client.post('/api/v1/auth/login/', {
            'email': 'newstaff01', 'password': 'Str0ng-pass-456',
        })
        assert response.status_code == 200
        assert response.data['user']['must_change_password'] is True

    def test_duplicate_username_rejected(self, organization, org_admin, agent_role, citizen):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(staff_url(organization), _payload(agent_role, username=citizen.username))
        assert response.status_code == 400
        assert 'username' in response.data.get('error', {}).get('field_errors', response.data)

    def test_duplicate_email_rejected(self, organization, org_admin, agent_role, citizen):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(staff_url(organization), _payload(agent_role, email=citizen.email))
        assert response.status_code == 400

    def test_weak_password_rejected(self, organization, org_admin, agent_role):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(staff_url(organization), _payload(agent_role, password='123'))
        assert response.status_code == 400
        assert not User.objects.filter(username='newstaff01').exists()

    def test_missing_role_rejected(self, organization, org_admin, agent_role):
        client = APIClient()
        client.force_authenticate(org_admin)
        payload = _payload(agent_role)
        del payload['role']
        response = client.post(staff_url(organization), payload)
        assert response.status_code == 400

    def test_requires_manage_staff_privilege_or_admin(self, organization, agent_role, citizen):
        client = APIClient()
        client.force_authenticate(citizen)
        response = client.post(staff_url(organization), _payload(agent_role))
        assert response.status_code == 403

    def test_role_from_other_org_rejected(self, organization, org_admin, other_organization, other_org_admin):
        foreign_role = StaffRole.objects.create(
            organization=other_organization, name='Foreign', privileges=[],
        )
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(staff_url(organization), _payload(foreign_role))
        assert response.status_code == 400
