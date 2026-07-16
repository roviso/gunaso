import pytest
from rest_framework.test import APIClient

from apps.organizations.models import OrganizationStaff, StaffRole
from apps.organizations.permissions import HasOrgPrivilege, require_privilege

pytestmark = pytest.mark.django_db

ORGS_URL = '/api/v1/organizations/'
SUBMISSIONS_URL = '/api/v1/submissions/'


# --- local fixtures -------------------------------------------------------
#
# These build on the shared `organization`/`citizen`/`submission` fixtures in
# conftest.py without changing them, so this file can add role/staff rows
# freely without touching other tests' expectations.

@pytest.fixture
def staff_user(django_user_model):
    return django_user_model.objects.create_user(
        username='staffmember', email='staffmember@ntc.example.com',
        password='Str0ng-pass-123', user_type='citizen',
    )


@pytest.fixture
def full_access_role(organization):
    """A role granting every privilege this subtask cares about."""
    return StaffRole.objects.create(
        organization=organization,
        name='Full Access',
        privileges=['view_submissions', 'manage_submissions', 'assign_submissions', 'view_stats'],
    )


@pytest.fixture
def no_access_role(organization):
    """A role granting an unrelated privilege only — deliberately missing the ones under test."""
    return StaffRole.objects.create(
        organization=organization, name='No Access', privileges=['manage_org_profile'],
    )


def make_staff(organization, user, role, status='active', is_active=True):
    return OrganizationStaff.objects.create(
        organization=organization, user=user, role=role, status=status, is_active=is_active,
    )


# --- HasOrgPrivilege unit-level behaviour ----------------------------------

class TestHasOrgPrivilegeUnit:
    def test_org_admin_always_allowed_even_without_privilege(self, organization, org_admin, rf):
        request = rf.get('/')
        request.user = org_admin
        assert HasOrgPrivilege('anything_not_in_catalog')._is_allowed(request, organization) is True

    def test_platform_staff_always_allowed(self, organization, platform_staff, rf):
        request = rf.get('/')
        request.user = platform_staff
        assert HasOrgPrivilege('anything_not_in_catalog')._is_allowed(request, organization) is True

    def test_unauthenticated_denied(self, organization, rf):
        from django.contrib.auth.models import AnonymousUser
        request = rf.get('/')
        request.user = AnonymousUser()
        assert HasOrgPrivilege('view_stats')._is_allowed(request, organization) is False

    def test_require_privilege_factory_is_zero_arg_constructible(self):
        cls = require_privilege('view_stats')
        instance = cls()
        assert instance.privilege == 'view_stats'


# --- Org-scoped endpoints: view_submissions / view_stats -------------------

class TestOrganizationSubmissionsPrivilege:
    url = None

    def _url(self, organization):
        return f'{ORGS_URL}{organization.slug}/submissions/'

    def test_active_staff_without_privilege_denied(self, organization, staff_user, no_access_role, submission):
        make_staff(organization, staff_user, no_access_role)
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.get(self._url(organization))
        assert response.status_code == 403

    def test_active_staff_with_privilege_allowed(self, organization, staff_user, full_access_role, submission):
        make_staff(organization, staff_user, full_access_role)
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.get(self._url(organization))
        assert response.status_code == 200

    def test_invited_but_not_accepted_staff_denied(self, organization, staff_user, full_access_role, submission):
        make_staff(organization, staff_user, full_access_role, status='invited')
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.get(self._url(organization))
        assert response.status_code == 403

    def test_disabled_staff_denied_even_with_active_status(self, organization, staff_user, full_access_role, submission):
        make_staff(organization, staff_user, full_access_role, status='active', is_active=False)
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.get(self._url(organization))
        assert response.status_code == 403


class TestAssignedToMeFilter:
    def _url(self, organization):
        return f'{ORGS_URL}{organization.slug}/submissions/?assigned_to=me'

    def test_returns_only_submissions_assigned_to_requesting_staff(
        self, organization, staff_user, full_access_role, submission, anonymous_submission, django_user_model,
    ):
        staff = make_staff(organization, staff_user, full_access_role)
        other_user = django_user_model.objects.create_user(
            username='otherstaff', email='otherstaff@ntc.example.com', password='Str0ng-pass-123',
        )
        other_staff = make_staff(organization, other_user, full_access_role)

        submission.assigned_to = staff
        submission.save(update_fields=['assigned_to'])
        anonymous_submission.assigned_to = other_staff
        anonymous_submission.save(update_fields=['assigned_to'])

        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.get(self._url(organization))
        assert response.status_code == 200
        ids = {row['reference_number'] for row in response.data['results']}
        assert ids == {submission.reference_number}

    def test_empty_when_nothing_assigned(self, organization, staff_user, full_access_role, submission):
        make_staff(organization, staff_user, full_access_role)
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.get(self._url(organization))
        assert response.status_code == 200
        assert response.data['results'] == []


class TestOrgAdminConvenienceEndpointsForStaff:
    """/org/submissions/ and /org/stats/ are the dashboard's own data
    endpoints — historically scoped to `organization__admin=request.user`,
    which silently returned nothing for staff. _resolve_org_for_request adds
    the active-staff fallback these depend on."""

    def test_org_submissions_visible_to_active_staff_with_privilege(
        self, organization, staff_user, full_access_role, submission,
    ):
        make_staff(organization, staff_user, full_access_role)
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.get('/api/v1/org/submissions/')
        assert response.status_code == 200
        refs = [s['reference_number'] for s in response.data['results']]
        assert submission.reference_number in refs

    def test_org_submissions_denied_to_staff_without_privilege(
        self, organization, staff_user, no_access_role, submission,
    ):
        make_staff(organization, staff_user, no_access_role)
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.get('/api/v1/org/submissions/')
        assert response.status_code == 403

    def test_org_submissions_assigned_to_me_scopes_to_requesting_staff(
        self, organization, staff_user, full_access_role, submission, django_user_model,
    ):
        staff = make_staff(organization, staff_user, full_access_role)
        submission.assigned_to = staff
        submission.save(update_fields=['assigned_to'])

        other_user = django_user_model.objects.create_user(
            username='otherstaffer', email='otherstaffer@ntc.example.com', password='Str0ng-pass-123',
        )
        make_staff(organization, other_user, full_access_role)

        client = APIClient()
        client.force_authenticate(other_user)
        response = client.get('/api/v1/org/submissions/?assigned_to=me')
        assert response.status_code == 200
        assert response.data['results'] == []

    def test_org_stats_visible_to_active_staff_with_privilege(self, organization, staff_user, full_access_role, submission):
        make_staff(organization, staff_user, full_access_role)
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.get('/api/v1/org/stats/')
        assert response.status_code == 200
        assert 'total' in response.data

    def test_org_stats_denied_to_staff_without_privilege(self, organization, staff_user, no_access_role, submission):
        make_staff(organization, staff_user, no_access_role)
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.get('/api/v1/org/stats/')
        assert response.status_code == 403

    def test_org_submissions_empty_for_user_with_no_org_relationship(self, citizen):
        client = APIClient()
        client.force_authenticate(citizen)
        response = client.get('/api/v1/org/submissions/')
        assert response.status_code == 200
        assert response.data['results'] == []

    def test_org_stats_404_for_user_with_no_org_relationship(self, citizen):
        client = APIClient()
        client.force_authenticate(citizen)
        response = client.get('/api/v1/org/stats/')
        assert response.status_code == 404


class TestOrganizationStatsPrivilege:
    def _url(self, organization):
        return f'{ORGS_URL}{organization.slug}/stats/'

    def test_active_staff_without_privilege_denied(self, organization, staff_user, no_access_role, submission):
        make_staff(organization, staff_user, no_access_role)
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.get(self._url(organization))
        assert response.status_code == 403

    def test_active_staff_with_privilege_allowed(self, organization, staff_user, full_access_role, submission):
        make_staff(organization, staff_user, full_access_role)
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.get(self._url(organization))
        assert response.status_code == 200

    def test_invited_but_not_accepted_staff_denied(self, organization, staff_user, full_access_role, submission):
        make_staff(organization, staff_user, full_access_role, status='invited')
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.get(self._url(organization))
        assert response.status_code == 403

    def test_disabled_staff_denied_even_with_active_status(self, organization, staff_user, full_access_role, submission):
        make_staff(organization, staff_user, full_access_role, status='active', is_active=False)
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.get(self._url(organization))
        assert response.status_code == 403


# --- Status-transition endpoint: manage_submissions -------------------------

class TestSubmissionStatusTransitionPrivilege:
    def _url(self, submission):
        return f'{SUBMISSIONS_URL}{submission.reference_number}/status/'

    def test_active_staff_without_privilege_denied(self, organization, staff_user, no_access_role, submission):
        make_staff(organization, staff_user, no_access_role)
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.patch(self._url(submission), {'status': 'acknowledged'})
        assert response.status_code == 403

    def test_active_staff_with_privilege_allowed(self, organization, staff_user, full_access_role, submission):
        make_staff(organization, staff_user, full_access_role)
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.patch(self._url(submission), {'status': 'acknowledged'})
        assert response.status_code == 200

    def test_invited_but_not_accepted_staff_denied(self, organization, staff_user, full_access_role, submission):
        make_staff(organization, staff_user, full_access_role, status='invited')
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.patch(self._url(submission), {'status': 'acknowledged'})
        assert response.status_code == 403

    def test_disabled_staff_denied_even_with_active_status(self, organization, staff_user, full_access_role, submission):
        make_staff(organization, staff_user, full_access_role, status='active', is_active=False)
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.patch(self._url(submission), {'status': 'acknowledged'})
        assert response.status_code == 403


# --- Assign endpoint: assign_submissions ------------------------------------

class TestSubmissionAssignPrivilege:
    def _url(self, submission):
        return f'{SUBMISSIONS_URL}{submission.reference_number}/assign/'

    def test_active_staff_without_privilege_denied(self, organization, staff_user, no_access_role, submission):
        assignee_role = StaffRole.objects.create(
            organization=organization, name='Assignee Role', privileges=['view_submissions'],
        )
        assignee = make_staff(organization, staff_user, no_access_role)
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.patch(self._url(submission), {'staff_id': assignee.id})
        assert response.status_code == 403

    def test_active_staff_with_privilege_allowed(self, organization, staff_user, full_access_role, submission):
        assignee = make_staff(organization, staff_user, full_access_role)
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.patch(self._url(submission), {'staff_id': assignee.id})
        assert response.status_code == 200
        submission.refresh_from_db()
        assert submission.assigned_to_id == assignee.id

    def test_invited_but_not_accepted_staff_denied(self, organization, staff_user, full_access_role, submission):
        assignee = make_staff(organization, staff_user, full_access_role, status='invited')
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.patch(self._url(submission), {'staff_id': assignee.id})
        assert response.status_code == 403

    def test_disabled_staff_denied_even_with_active_status(self, organization, staff_user, full_access_role, submission):
        assignee = make_staff(organization, staff_user, full_access_role, status='active', is_active=False)
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.patch(self._url(submission), {'staff_id': assignee.id})
        assert response.status_code == 403

    def test_org_admin_can_always_assign(self, organization, org_admin, staff_user, no_access_role, submission):
        assignee = make_staff(organization, staff_user, no_access_role)
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.patch(self._url(submission), {'staff_id': assignee.id})
        assert response.status_code == 200


# --- Serializer: assigned_to.role reads staff.role.name ---------------------

class TestAssignedToSerialization:
    def test_assigned_to_role_is_role_name_not_fk_repr(self, organization, org_admin, staff_user, full_access_role, submission):
        assignee = make_staff(organization, staff_user, full_access_role)
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.patch(
            f'{SUBMISSIONS_URL}{submission.reference_number}/assign/', {'staff_id': assignee.id}
        )
        assert response.status_code == 200
        assert response.data['assigned_to']['role'] == full_access_role.name
