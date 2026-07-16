from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from apps.organizations.models import OrganizationStaff, StaffInvite, StaffRole
from apps.organizations.services import _hash_token

pytestmark = pytest.mark.django_db

ORGS_URL = '/api/v1/organizations/'


# --- local fixtures ---------------------------------------------------------

@pytest.fixture
def agent_role(organization):
    return StaffRole.objects.create(
        organization=organization, name='Agent', privileges=['view_submissions'],
    )


@pytest.fixture
def manage_staff_role(organization):
    return StaffRole.objects.create(
        organization=organization, name='Staff Manager', privileges=['manage_staff'],
    )


def staff_url(organization):
    return f'{ORGS_URL}{organization.slug}/staff/'


def resend_url(organization, staff):
    return f'{ORGS_URL}{organization.slug}/staff/{staff.id}/resend-invite/'


def preview_url(token):
    return f'{ORGS_URL}invite/{token}/'


def accept_url(token):
    return f'{ORGS_URL}invite/{token}/accept/'


def _latest_invite_token_from_mail():
    """Pull the raw invite token out of the single outgoing email's body."""
    assert len(mail.outbox) == 1
    body = mail.outbox[0].body
    # The link is the only thing on its own line in the email body template.
    for line in body.splitlines():
        if '/invite/' in line:
            return line.strip().rsplit('/', 1)[-1]
    raise AssertionError('No invite link found in email body')


# --- Create-or-invite: existing usable-password user ------------------------

class TestAttachExistingUser:
    def test_existing_active_user_attached_immediately_no_email_required(
        self, organization, org_admin, citizen, agent_role,
    ):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(
            staff_url(organization), {'user_email': citizen.email, 'role': agent_role.id},
        )
        assert response.status_code == 201
        assert response.data['status'] == 'active'
        assert response.data['invited'] is False

        staff = OrganizationStaff.objects.get(organization=organization, user=citizen)
        assert staff.status == 'active'
        assert not StaffInvite.objects.filter(staff=staff).exists()

    def test_duplicate_staff_member_rejected(self, organization, org_admin, citizen, agent_role):
        OrganizationStaff.objects.create(
            organization=organization, user=citizen, role=agent_role, status='active',
        )
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(
            staff_url(organization), {'user_email': citizen.email, 'role': agent_role.id},
        )
        assert response.status_code == 400


# --- Create-or-invite: brand-new email --------------------------------------

class TestInviteNewEmail:
    def test_new_email_creates_pending_user_and_sends_one_email(
        self, organization, org_admin, agent_role,
    ):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(
            staff_url(organization),
            {'user_email': 'newhire@ntc.example.com', 'role': agent_role.id},
        )
        assert response.status_code == 201
        assert response.data['status'] == 'invited'
        assert response.data['invited'] is True
        # The raw token is deliberately included via `invite_link` (copy-link
        # fallback for when email delivery isn't configured) — but never as a
        # bare token field, and only visible to the inviting admin.
        assert 'token' not in {k.lower() for k in response.data}

        staff = OrganizationStaff.objects.get(organization=organization, user__email='newhire@ntc.example.com')
        assert staff.status == 'invited'
        assert staff.user.is_active is False
        assert not staff.user.has_usable_password()

        invite = StaffInvite.objects.get(staff=staff)
        assert invite.accepted_at is None
        # Only the hash is ever persisted.
        assert invite.token_hash != ''
        assert len(invite.token_hash) == 64  # sha256 hex digest

        assert len(mail.outbox) == 1
        assert staff.user.email in mail.outbox[0].to
        assert '/invite/' in mail.outbox[0].body
        assert '/staff/invite/' not in mail.outbox[0].body  # must match the SPA route, not the old broken path

        assert response.data['invite_link'].startswith('http')
        assert response.data['invite_link'].endswith(_latest_invite_token_from_mail())

    def test_invited_staff_cannot_log_in_before_accepting(self, organization, org_admin, agent_role):
        client = APIClient()
        client.force_authenticate(org_admin)
        client.post(staff_url(organization), {'user_email': 'newhire@ntc.example.com', 'role': agent_role.id})

        login_response = APIClient().post(
            '/api/v1/auth/login/', {'email': 'newhire@ntc.example.com', 'password': 'anything-at-all'},
        )
        assert login_response.status_code == 401


# --- Invite preview -----------------------------------------------------------

class TestInvitePreview:
    def _create_invite(self, organization, org_admin, agent_role, email='newhire@ntc.example.com'):
        client = APIClient()
        client.force_authenticate(org_admin)
        client.post(staff_url(organization), {'user_email': email, 'role': agent_role.id})
        return _latest_invite_token_from_mail()

    def test_valid_token_returns_org_role_and_email(self, organization, org_admin, agent_role):
        token = self._create_invite(organization, org_admin, agent_role)
        response = APIClient().get(preview_url(token))
        assert response.status_code == 200
        assert response.data['organization'] == organization.name
        assert response.data['role'] == agent_role.name
        assert response.data['email'] == 'newhire@ntc.example.com'

    def test_unknown_token_returns_bare_404(self):
        response = APIClient().get(preview_url('not-a-real-token'))
        assert response.status_code == 404

    def test_expired_token_returns_404_not_a_detailed_error(self, organization, org_admin, agent_role):
        token = self._create_invite(organization, org_admin, agent_role)
        StaffInvite.objects.update(expires_at=timezone.now() - timedelta(days=1))
        response = APIClient().get(preview_url(token))
        assert response.status_code == 404

    def test_already_accepted_token_returns_404(self, organization, org_admin, agent_role):
        token = self._create_invite(organization, org_admin, agent_role)
        accept_response = APIClient().post(accept_url(token), {'password': 'Str0ng-pass-456'})
        assert accept_response.status_code == 200
        response = APIClient().get(preview_url(token))
        assert response.status_code == 404


# --- Invite accept -------------------------------------------------------------

class TestInviteAccept:
    def _create_invite(self, organization, org_admin, agent_role, email='newhire@ntc.example.com'):
        client = APIClient()
        client.force_authenticate(org_admin)
        client.post(staff_url(organization), {'user_email': email, 'role': agent_role.id})
        return _latest_invite_token_from_mail()

    def test_valid_token_succeeds_and_returns_access_token(self, organization, org_admin, agent_role):
        token = self._create_invite(organization, org_admin, agent_role)
        response = APIClient().post(accept_url(token), {'password': 'Str0ng-pass-456'})
        assert response.status_code == 200
        assert 'access' in response.data
        assert response.data['user']['email'] == 'newhire@ntc.example.com'

        staff = OrganizationStaff.objects.get(organization=organization, user__email='newhire@ntc.example.com')
        assert staff.status == 'active'
        assert staff.user.is_active is True
        assert staff.user.has_usable_password()

        invite = StaffInvite.objects.get(staff=staff)
        assert invite.accepted_at is not None

    def test_weak_password_rejected(self, organization, org_admin, agent_role):
        token = self._create_invite(organization, org_admin, agent_role)
        response = APIClient().post(accept_url(token), {'password': '123'})
        assert response.status_code == 400

    def test_expired_token_fails(self, organization, org_admin, agent_role):
        token = self._create_invite(organization, org_admin, agent_role)
        StaffInvite.objects.update(expires_at=timezone.now() - timedelta(days=1))
        response = APIClient().post(accept_url(token), {'password': 'Str0ng-pass-456'})
        assert response.status_code in (400, 410)

    def test_already_accepted_token_cannot_be_reused(self, organization, org_admin, agent_role):
        token = self._create_invite(organization, org_admin, agent_role)
        first = APIClient().post(accept_url(token), {'password': 'Str0ng-pass-456'})
        assert first.status_code == 200

        second = APIClient().post(accept_url(token), {'password': 'Another-Str0ng-789'})
        assert second.status_code in (400, 410)

    def test_unknown_token_fails(self):
        response = APIClient().post(accept_url('not-a-real-token'), {'password': 'Str0ng-pass-456'})
        assert response.status_code in (400, 410)


# --- Resend invite --------------------------------------------------------------

class TestResendInvite:
    def _create_invite(self, organization, org_admin, agent_role, email='newhire@ntc.example.com'):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(staff_url(organization), {'user_email': email, 'role': agent_role.id})
        staff = OrganizationStaff.objects.get(pk=response.data['id'])
        old_token = _latest_invite_token_from_mail()
        return staff, old_token

    def test_resend_invalidates_prior_token(self, organization, org_admin, agent_role):
        staff, old_token = self._create_invite(organization, org_admin, agent_role)
        mail.outbox.clear()

        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(resend_url(organization, staff))
        assert response.status_code == 200
        assert len(mail.outbox) == 1

        new_token = _latest_invite_token_from_mail()
        assert new_token != old_token

        # The old link no longer works...
        old_accept = APIClient().post(accept_url(old_token), {'password': 'Str0ng-pass-456'})
        assert old_accept.status_code in (400, 410)

        # ...but the new one does.
        new_accept = APIClient().post(accept_url(new_token), {'password': 'Str0ng-pass-456'})
        assert new_accept.status_code == 200

    def test_resend_requires_manage_staff_privilege_or_admin(
        self, organization, org_admin, agent_role, manage_staff_role, django_user_model,
    ):
        staff, _old_token = self._create_invite(organization, org_admin, agent_role)

        # A staff member without 'manage_staff' is denied.
        no_access_user = django_user_model.objects.create_user(
            username='noaccess', email='noaccess@ntc.example.com',
            password='Str0ng-pass-123', user_type='citizen',
        )
        OrganizationStaff.objects.create(
            organization=organization, user=no_access_user, role=agent_role, status='active',
        )
        client = APIClient()
        client.force_authenticate(no_access_user)
        response = client.post(resend_url(organization, staff))
        assert response.status_code == 403

        # A staff member with 'manage_staff' is allowed.
        manager_user = django_user_model.objects.create_user(
            username='staffmanager', email='staffmanager@ntc.example.com',
            password='Str0ng-pass-123', user_type='citizen',
        )
        OrganizationStaff.objects.create(
            organization=organization, user=manager_user, role=manage_staff_role, status='active',
        )
        client2 = APIClient()
        client2.force_authenticate(manager_user)
        response2 = client2.post(resend_url(organization, staff))
        assert response2.status_code == 200

    def test_resend_on_already_active_staff_returns_400(self, organization, org_admin, citizen, agent_role):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(staff_url(organization), {'user_email': citizen.email, 'role': agent_role.id})
        staff = OrganizationStaff.objects.get(pk=response.data['id'])
        assert staff.status == 'active'

        resend_response = client.post(resend_url(organization, staff))
        assert resend_response.status_code == 400


# --- Token hashing sanity check --------------------------------------------

def test_raw_token_never_persisted():
    """Only the hash is stored; the raw value can't be recovered from the DB."""
    raw = 'some-raw-token-value'
    hashed = _hash_token(raw)
    assert hashed != raw
    assert len(hashed) == 64
