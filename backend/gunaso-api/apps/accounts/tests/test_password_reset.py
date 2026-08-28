"""Forgot-password flow: request a link, then set a new password with it.

Covers the two properties the flow exists to guarantee — that the emailed
uid/token pair is the only way to set the password, and that requesting a
reset never reveals whether an account exists (CLAUDE.md section 8).
"""
import pytest
from django.core import mail
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.services import generate_password_reset_credentials

REQUEST_URL = reverse('auth-password-reset')
CONFIRM_URL = reverse('auth-password-reset-confirm')
LOGIN_URL = reverse('auth-login')

NEW_PASSWORD = 'Br4nd-New-Pass-99'


@pytest.fixture
def api():
    return APIClient()


def _link_credentials(user):
    """The (uid, token) a real request would have emailed."""
    return generate_password_reset_credentials(user)


# ──────────────────────────────────────────────────────────────────────────────
# Requesting a link
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_request_sends_email_with_reset_link(api, citizen, settings):
    settings.FRONTEND_URL = 'http://localhost:3000'

    response = api.post(REQUEST_URL, {'email': citizen.email}, format='json')

    assert response.status_code == 200
    assert len(mail.outbox) == 1
    sent = mail.outbox[0]
    assert sent.to == [citizen.email]
    assert 'http://localhost:3000/reset-password/' in sent.body
    # Multipart: the HTML alternative carries the same link.
    html_body = sent.alternatives[0][0]
    assert 'http://localhost:3000/reset-password/' in html_body


@pytest.mark.django_db
def test_request_is_case_insensitive_on_email(api, citizen):
    response = api.post(REQUEST_URL, {'email': citizen.email.upper()}, format='json')

    assert response.status_code == 200
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_request_for_unknown_email_looks_identical_but_sends_nothing(api, citizen):
    known = api.post(REQUEST_URL, {'email': citizen.email}, format='json')
    mail.outbox.clear()

    unknown = api.post(REQUEST_URL, {'email': 'nobody@example.com'}, format='json')

    # No account enumeration: same status, same body.
    assert unknown.status_code == known.status_code == 200
    assert unknown.data == known.data
    assert mail.outbox == []


@pytest.mark.django_db
def test_request_for_inactive_account_sends_nothing(api, citizen):
    citizen.is_active = False
    citizen.save(update_fields=['is_active'])

    response = api.post(REQUEST_URL, {'email': citizen.email}, format='json')

    assert response.status_code == 200
    assert mail.outbox == []


@pytest.mark.django_db
def test_request_for_pending_invite_account_sends_nothing(api, django_user_model):
    """An unaccepted staff invite has an unusable password; letting a reset
    link stand in for the single-use invite link would bypass that flow."""
    invitee = django_user_model.objects.create(
        username='pending', email='pending@example.com', is_active=False,
    )
    invitee.set_unusable_password()
    invitee.is_active = True
    invitee.save()

    response = api.post(REQUEST_URL, {'email': invitee.email}, format='json')

    assert response.status_code == 200
    assert mail.outbox == []


@pytest.mark.django_db
def test_request_rejects_malformed_email(api):
    response = api.post(REQUEST_URL, {'email': 'not-an-email'}, format='json')

    assert response.status_code == 400
    assert mail.outbox == []


@pytest.mark.django_db
def test_request_survives_a_broken_smtp_host(api, citizen, settings, monkeypatch):
    """A dead mail server must not 500, and must not leak that the account
    exists by failing differently from the unknown-email case."""
    from apps.accounts import services

    monkeypatch.setattr(
        services, 'send_password_reset_email',
        lambda *a, **kw: (_ for _ in ()).throw(OSError('smtp down')),
    )

    response = api.post(REQUEST_URL, {'email': citizen.email}, format='json')

    assert response.status_code == 200


# ──────────────────────────────────────────────────────────────────────────────
# Confirming with the link
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_confirm_sets_the_new_password(api, citizen):
    uid, token = _link_credentials(citizen)

    response = api.post(
        CONFIRM_URL, {'uid': uid, 'token': token, 'new_password': NEW_PASSWORD}, format='json',
    )

    assert response.status_code == 200
    citizen.refresh_from_db()
    assert citizen.check_password(NEW_PASSWORD)


@pytest.mark.django_db
def test_can_log_in_with_the_new_password_and_not_the_old(api, citizen):
    uid, token = _link_credentials(citizen)
    api.post(CONFIRM_URL, {'uid': uid, 'token': token, 'new_password': NEW_PASSWORD}, format='json')

    old = api.post(
        LOGIN_URL, {'email': citizen.email, 'password': 'Str0ng-pass-123'}, format='json',
    )
    new = api.post(LOGIN_URL, {'email': citizen.email, 'password': NEW_PASSWORD}, format='json')

    assert old.status_code == 401
    assert new.status_code == 200


@pytest.mark.django_db
def test_link_cannot_be_reused(api, citizen):
    """default_token_generator hashes the password, so setting a new one
    invalidates the link that set it."""
    uid, token = _link_credentials(citizen)
    first = api.post(
        CONFIRM_URL, {'uid': uid, 'token': token, 'new_password': NEW_PASSWORD}, format='json',
    )

    second = api.post(
        CONFIRM_URL, {'uid': uid, 'token': token, 'new_password': 'Yet-An0ther-Pass'}, format='json',
    )

    assert first.status_code == 200
    assert second.status_code == 400
    citizen.refresh_from_db()
    assert citizen.check_password(NEW_PASSWORD)


@pytest.mark.django_db
def test_confirm_rejects_a_tampered_token(api, citizen):
    uid, token = _link_credentials(citizen)

    response = api.post(
        CONFIRM_URL,
        {'uid': uid, 'token': token + 'x', 'new_password': NEW_PASSWORD},
        format='json',
    )

    assert response.status_code == 400
    citizen.refresh_from_db()
    assert not citizen.check_password(NEW_PASSWORD)


@pytest.mark.django_db
def test_confirm_rejects_another_users_token(api, citizen, org_admin):
    """A token is bound to the uid it was issued for — pairing it with a
    different account's uid must not work."""
    _, token = _link_credentials(citizen)
    other_uid, _ = _link_credentials(org_admin)

    response = api.post(
        CONFIRM_URL,
        {'uid': other_uid, 'token': token, 'new_password': NEW_PASSWORD},
        format='json',
    )

    assert response.status_code == 400
    org_admin.refresh_from_db()
    assert not org_admin.check_password(NEW_PASSWORD)


@pytest.mark.django_db
def test_confirm_rejects_garbage_uid(api):
    response = api.post(
        CONFIRM_URL,
        {'uid': 'not-base64!!', 'token': 'whatever', 'new_password': NEW_PASSWORD},
        format='json',
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_confirm_rejects_missing_uid_and_token(api):
    response = api.post(CONFIRM_URL, {'new_password': NEW_PASSWORD}, format='json')

    assert response.status_code == 400


@pytest.mark.django_db
def test_confirm_enforces_password_validators(api, citizen):
    uid, token = _link_credentials(citizen)

    response = api.post(
        CONFIRM_URL, {'uid': uid, 'token': token, 'new_password': 'abc'}, format='json',
    )

    assert response.status_code == 400
    citizen.refresh_from_db()
    assert not citizen.check_password('abc')


@pytest.mark.django_db
def test_confirm_blacklists_outstanding_refresh_tokens(api, citizen):
    """Resetting is what someone does after a suspected takeover — an already
    issued refresh token must not outlive it."""
    stolen = RefreshToken.for_user(citizen)
    uid, token = _link_credentials(citizen)

    api.post(CONFIRM_URL, {'uid': uid, 'token': token, 'new_password': NEW_PASSWORD}, format='json')

    assert BlacklistedToken.objects.filter(token__jti=stolen.payload['jti']).exists()


@pytest.mark.django_db
def test_confirm_clears_forced_password_change(api, citizen):
    citizen.must_change_password = True
    citizen.save(update_fields=['must_change_password'])
    uid, token = _link_credentials(citizen)

    api.post(CONFIRM_URL, {'uid': uid, 'token': token, 'new_password': NEW_PASSWORD}, format='json')

    citizen.refresh_from_db()
    assert citizen.must_change_password is False


@pytest.mark.django_db
def test_end_to_end_from_the_emailed_link(api, citizen, settings):
    """Parse the link out of the actual email body the way a user's browser
    would, and drive the confirm endpoint with it."""
    settings.FRONTEND_URL = 'http://localhost:3000'
    api.post(REQUEST_URL, {'email': citizen.email}, format='json')

    link = next(
        word for word in mail.outbox[0].body.split()
        if word.startswith('http://localhost:3000/reset-password/')
    )
    uid, token = link.rsplit('/', 2)[-2:]

    response = api.post(
        CONFIRM_URL, {'uid': uid, 'token': token, 'new_password': NEW_PASSWORD}, format='json',
    )

    assert response.status_code == 200
    citizen.refresh_from_db()
    assert citizen.check_password(NEW_PASSWORD)
