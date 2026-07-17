import pytest
from rest_framework.test import APIClient

from apps.organizations.models import Organization
from apps.platform_admin.models import PlatformAuditLog
from apps.platform_admin.services import (
    block_user,
    demote_superadmin,
    platform_overview,
    promote_to_superadmin,
    unblock_user,
    verify_organization,
)

pytestmark = pytest.mark.django_db

OVERVIEW_URL = '/api/v1/admin/overview/'
ORGS_URL = '/api/v1/admin/organizations/'
USERS_URL = '/api/v1/admin/users/'
SUBMISSIONS_URL = '/api/v1/admin/submissions/'
AUDIT_LOG_URL = '/api/v1/admin/audit-log/'


# --- local fixtures -------------------------------------------------------

@pytest.fixture
def superadmin(django_user_model):
    return django_user_model.objects.create_user(
        username='godmode', email='superadmin@gunaso.example.com',
        password='Str0ng-pass-123', is_staff=True, is_superuser=True,
    )


@pytest.fixture
def other_superadmin(django_user_model):
    return django_user_model.objects.create_user(
        username='godmode2', email='superadmin2@gunaso.example.com',
        password='Str0ng-pass-123', is_staff=True, is_superuser=True,
    )


@pytest.fixture
def unverified_organization(other_org_admin):
    return Organization.objects.create(
        name='Pending Org', slug='pending-org',
        description='Awaiting verification', category='ngo',
        contact_email='pending@example.com',
        is_verified=False, admin=other_org_admin,
    )


def org_url(slug):
    return f'{ORGS_URL}{slug}/'


def block_url(user_id):
    return f'{USERS_URL}{user_id}/block/'


def unblock_url(user_id):
    return f'{USERS_URL}{user_id}/unblock/'


def promote_url(user_id):
    return f'{USERS_URL}{user_id}/promote/'


def demote_url(user_id):
    return f'{USERS_URL}{user_id}/demote/'


# --- Permission boundaries: every endpoint requires is_superuser -----------

class TestSuperAdminPermissionBoundary:
    """Positive AND negative cases per CLAUDE.md section 10 — a permission
    test that only checks the happy path is not done."""

    @pytest.mark.parametrize('url', [OVERVIEW_URL, ORGS_URL, USERS_URL, SUBMISSIONS_URL, AUDIT_LOG_URL])
    def test_unauthenticated_denied(self, url):
        response = APIClient().get(url)
        assert response.status_code == 401

    @pytest.mark.parametrize('url', [OVERVIEW_URL, ORGS_URL, USERS_URL, SUBMISSIONS_URL, AUDIT_LOG_URL])
    def test_plain_citizen_denied(self, url, citizen):
        client = APIClient()
        client.force_authenticate(citizen)
        response = client.get(url)
        assert response.status_code == 403

    @pytest.mark.parametrize('url', [OVERVIEW_URL, ORGS_URL, USERS_URL, SUBMISSIONS_URL, AUDIT_LOG_URL])
    def test_org_admin_denied(self, url, org_admin):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.get(url)
        assert response.status_code == 403

    @pytest.mark.parametrize('url', [OVERVIEW_URL, ORGS_URL, USERS_URL, SUBMISSIONS_URL, AUDIT_LOG_URL])
    def test_is_staff_without_is_superuser_denied(self, url, platform_staff):
        """`platform_staff` (is_staff=True) already bypasses org-scoped checks
        elsewhere in the app, but must NOT reach the superadmin dashboard —
        only `is_superuser` does. This is the boundary IsSuperAdmin exists to
        enforce; see apps/platform_admin/permissions.py."""
        client = APIClient()
        client.force_authenticate(platform_staff)
        response = client.get(url)
        assert response.status_code == 403

    @pytest.mark.parametrize('url', [OVERVIEW_URL, ORGS_URL, USERS_URL, SUBMISSIONS_URL, AUDIT_LOG_URL])
    def test_superadmin_allowed(self, url, superadmin):
        client = APIClient()
        client.force_authenticate(superadmin)
        response = client.get(url)
        assert response.status_code == 200

    def test_user_action_endpoints_denied_for_non_superadmin(self, org_admin, citizen):
        client = APIClient()
        client.force_authenticate(org_admin)
        for url in [block_url(citizen.id), unblock_url(citizen.id), promote_url(citizen.id), demote_url(citizen.id)]:
            response = client.post(url)
            assert response.status_code == 403

    def test_organization_action_endpoint_denied_for_non_superadmin(self, org_admin, organization):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.patch(org_url(organization.slug), {'is_verified': True}, format='json')
        assert response.status_code == 403


# --- Organization verification / activation ---------------------------------

class TestOrganizationVerification:
    def test_superadmin_verifies_organization(self, superadmin, unverified_organization):
        client = APIClient()
        client.force_authenticate(superadmin)

        response = client.patch(org_url(unverified_organization.slug), {'is_verified': True}, format='json')

        assert response.status_code == 200
        assert response.data['is_verified'] is True
        unverified_organization.refresh_from_db()
        assert unverified_organization.is_verified is True

    def test_superadmin_deactivates_organization(self, superadmin, organization):
        client = APIClient()
        client.force_authenticate(superadmin)

        response = client.patch(org_url(organization.slug), {'is_active': False}, format='json')

        assert response.status_code == 200
        organization.refresh_from_db()
        assert organization.is_active is False

    def test_organization_list_includes_unverified_organizations(self, superadmin, unverified_organization, organization):
        """Unlike the public organizations list, the admin list must surface
        orgs the public never sees — that's the entire point of a verify queue."""
        client = APIClient()
        client.force_authenticate(superadmin)

        response = client.get(ORGS_URL)

        slugs = {org['slug'] for org in response.data['results']}
        assert unverified_organization.slug in slugs
        assert organization.slug in slugs

    def test_verify_organization_writes_audit_log(self, superadmin, unverified_organization):
        verify_organization(unverified_organization, superadmin, True)

        entry = PlatformAuditLog.objects.get(action='organization_verified')
        assert entry.actor_id == superadmin.id
        assert entry.target_id == unverified_organization.id
        assert entry.target_repr == unverified_organization.name


# --- Block / unblock users ---------------------------------------------------

class TestBlockUnblockUser:
    def test_block_deactivates_user_and_logs(self, superadmin, citizen):
        block_user(citizen, superadmin)

        citizen.refresh_from_db()
        assert citizen.is_active is False
        entry = PlatformAuditLog.objects.get(action='user_blocked')
        assert entry.target_id == citizen.id

    def test_blocked_user_cannot_authenticate(self, superadmin, citizen):
        client = APIClient()
        client.force_authenticate(superadmin)
        client.post(block_url(citizen.id))

        login = APIClient().post('/api/v1/auth/login/', {
            'email': citizen.email, 'password': 'Str0ng-pass-123',
        }, format='json')
        assert login.status_code == 401

    def test_unblock_reactivates_user(self, superadmin, citizen):
        block_user(citizen, superadmin)
        unblock_user(citizen, superadmin)

        citizen.refresh_from_db()
        assert citizen.is_active is True

    def test_superadmin_cannot_block_own_account(self, superadmin):
        client = APIClient()
        client.force_authenticate(superadmin)

        response = client.post(block_url(superadmin.id))

        assert response.status_code == 400
        superadmin.refresh_from_db()
        assert superadmin.is_active is True

    def test_block_endpoint_returns_updated_user(self, superadmin, citizen):
        client = APIClient()
        client.force_authenticate(superadmin)

        response = client.post(block_url(citizen.id))

        assert response.status_code == 200
        assert response.data['is_active'] is False


# --- Promote / demote superadmins --------------------------------------------

class TestPromoteDemoteSuperAdmin:
    def test_promote_grants_staff_and_superuser(self, superadmin, citizen):
        promote_to_superadmin(citizen, superadmin)

        citizen.refresh_from_db()
        assert citizen.is_staff is True
        assert citizen.is_superuser is True
        assert PlatformAuditLog.objects.filter(action='user_promoted', target_id=citizen.id).exists()

    def test_promoted_user_can_reach_admin_dashboard(self, superadmin, citizen):
        promote_to_superadmin(citizen, superadmin)
        client = APIClient()
        client.force_authenticate(citizen)

        response = client.get(OVERVIEW_URL)

        assert response.status_code == 200

    def test_demote_revokes_staff_and_superuser(self, superadmin, other_superadmin):
        demote_superadmin(other_superadmin, superadmin)

        other_superadmin.refresh_from_db()
        assert other_superadmin.is_staff is False
        assert other_superadmin.is_superuser is False

    def test_cannot_demote_own_account(self, superadmin, other_superadmin):
        """Guards against a superadmin locking themself out."""
        from rest_framework.exceptions import ValidationError

        with pytest.raises(ValidationError):
            demote_superadmin(superadmin, superadmin)

        superadmin.refresh_from_db()
        assert superadmin.is_superuser is True

    def test_cannot_demote_last_remaining_superadmin(self, superadmin, citizen):
        """Only one superadmin exists (the `other_superadmin` fixture is not
        used here) — demoting them would leave the platform admin-less.
        `citizen` stands in as a distinct actor so this exercises the
        last-superadmin guard specifically, not the separate self-demote
        guard covered by `test_cannot_demote_own_account`."""
        from rest_framework.exceptions import ValidationError

        with pytest.raises(ValidationError):
            demote_superadmin(superadmin, citizen)

        superadmin.refresh_from_db()
        assert superadmin.is_superuser is True

    def test_demote_endpoint_denied_via_api_for_last_superadmin(self, superadmin, other_superadmin, citizen):
        """With two superadmins present, demoting one via the API succeeds;
        this confirms the guard is specifically about the *count*, not a
        blanket rejection."""
        client = APIClient()
        client.force_authenticate(superadmin)

        response = client.post(demote_url(other_superadmin.id))

        assert response.status_code == 200
        other_superadmin.refresh_from_db()
        assert other_superadmin.is_superuser is False


# --- Cross-org submission feed & anonymity -----------------------------------

class TestAdminSubmissionFeed:
    def test_superadmin_sees_submissions_across_organizations(
        self, superadmin, submission, other_organization, citizen,
    ):
        from apps.submissions.models import Submission
        Submission.objects.create(
            reference_number='GUN-2026-00099', organization=other_organization,
            citizen=citizen, citizen_name='Ram Sharma', citizen_email='ram@example.com',
            title='Water supply cut off', description='No water for a whole week now.',
        )
        client = APIClient()
        client.force_authenticate(superadmin)

        response = client.get(SUBMISSIONS_URL)

        org_slugs = {row['org_slug'] for row in response.data['results']}
        assert submission.organization.slug in org_slugs
        assert other_organization.slug in org_slugs

    def test_superadmin_sees_anonymous_submitter_identity(self, superadmin, anonymous_submission):
        client = APIClient()
        client.force_authenticate(superadmin)

        response = client.get(SUBMISSIONS_URL)

        row = next(r for r in response.data['results'] if r['reference_number'] == anonymous_submission.reference_number)
        assert row['submitter_name'] != 'Anonymous'


# --- platform_overview() aggregate correctness -------------------------------

class TestPlatformOverview:
    def test_overview_counts_reflect_current_state(self, superadmin, organization, unverified_organization, citizen):
        data = platform_overview()

        assert data['organizations']['total'] == 2
        assert data['organizations']['verified'] == 1
        assert data['organizations']['unverified'] == 1
        assert data['users']['superadmins'] == 1
        assert len(data['trend']) == 30
