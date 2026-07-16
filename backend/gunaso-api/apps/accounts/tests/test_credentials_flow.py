import pytest
from django.core import mail
from rest_framework.test import APIClient

from apps.accounts.services import generate_email_verification_token

pytestmark = pytest.mark.django_db

LOGIN_URL = '/api/v1/auth/login/'
CHANGE_PASSWORD_URL = '/api/v1/auth/change-password/'
VERIFY_REQUEST_URL = '/api/v1/auth/email-verification/request/'
VERIFY_CONFIRM_URL = '/api/v1/auth/email-verification/confirm/'


@pytest.fixture
def staff_user(django_user_model):
    user = django_user_model.objects.create_user(
        username='newhirebot', email='newhirebot@ntc.example.com',
        password='Str0ng-pass-123', user_type='citizen',
    )
    user.must_change_password = True
    user.email_verified = False
    user.save(update_fields=['must_change_password', 'email_verified'])
    return user


class TestLoginByUsernameOrEmail:
    def test_login_with_username_succeeds(self, citizen):
        client = APIClient()
        response = client.post(LOGIN_URL, {'email': citizen.username, 'password': 'Str0ng-pass-123'})
        assert response.status_code == 200
        assert response.data['user']['email'] == citizen.email

    def test_login_with_email_still_works(self, citizen):
        client = APIClient()
        response = client.post(LOGIN_URL, {'email': citizen.email, 'password': 'Str0ng-pass-123'})
        assert response.status_code == 200

    def test_login_with_unknown_identifier_fails_generically(self):
        client = APIClient()
        response = client.post(LOGIN_URL, {'email': 'nobody-here', 'password': 'whatever'})
        assert response.status_code == 401

    def test_must_change_password_surfaces_on_login(self, staff_user):
        client = APIClient()
        response = client.post(LOGIN_URL, {'email': staff_user.username, 'password': 'Str0ng-pass-123'})
        assert response.status_code == 200
        assert response.data['user']['must_change_password'] is True
        assert response.data['user']['email_verified'] is False


class TestChangePassword:
    def test_change_password_clears_flag(self, staff_user):
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.post(CHANGE_PASSWORD_URL, {
            'current_password': 'Str0ng-pass-123', 'new_password': 'Br4nd-new-pass-789',
        })
        assert response.status_code == 200
        assert response.data['user']['must_change_password'] is False

        staff_user.refresh_from_db()
        assert staff_user.must_change_password is False
        assert staff_user.check_password('Br4nd-new-pass-789')

    def test_wrong_current_password_rejected(self, staff_user):
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.post(CHANGE_PASSWORD_URL, {
            'current_password': 'totally-wrong', 'new_password': 'Br4nd-new-pass-789',
        })
        assert response.status_code == 400
        staff_user.refresh_from_db()
        assert staff_user.must_change_password is True

    def test_weak_new_password_rejected(self, staff_user):
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.post(CHANGE_PASSWORD_URL, {
            'current_password': 'Str0ng-pass-123', 'new_password': '123',
        })
        assert response.status_code == 400

    def test_unauthenticated_rejected(self):
        client = APIClient()
        response = client.post(CHANGE_PASSWORD_URL, {
            'current_password': 'x', 'new_password': 'Br4nd-new-pass-789',
        })
        assert response.status_code == 401


class TestEmailVerification:
    def test_request_sends_email_and_allows_email_correction(self, staff_user):
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.post(VERIFY_REQUEST_URL, {'email': 'corrected@ntc.example.com'})
        assert response.status_code == 200
        assert len(mail.outbox) == 1
        assert 'corrected@ntc.example.com' in mail.outbox[0].to

        staff_user.refresh_from_db()
        assert staff_user.email == 'corrected@ntc.example.com'
        assert staff_user.email_verified is False

    def test_request_rejects_email_already_taken(self, staff_user, citizen):
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.post(VERIFY_REQUEST_URL, {'email': citizen.email})
        assert response.status_code == 400

    def test_already_verified_user_cannot_request_again(self, citizen):
        client = APIClient()
        client.force_authenticate(citizen)
        response = client.post(VERIFY_REQUEST_URL, {})
        assert response.status_code == 400

    def test_confirm_with_valid_token_marks_verified(self, staff_user):
        token = generate_email_verification_token(staff_user)
        client = APIClient()
        response = client.post(VERIFY_CONFIRM_URL, {'token': token})
        assert response.status_code == 200

        staff_user.refresh_from_db()
        assert staff_user.email_verified is True

    def test_confirm_does_not_require_authentication(self, staff_user):
        token = generate_email_verification_token(staff_user)
        client = APIClient()
        client.credentials()
        response = client.post(VERIFY_CONFIRM_URL, {'token': token})
        assert response.status_code == 200

    def test_confirm_with_garbage_token_rejected(self):
        client = APIClient()
        response = client.post(VERIFY_CONFIRM_URL, {'token': 'not-a-real-token'})
        assert response.status_code == 400

    def test_confirm_with_expired_token_rejected(self, staff_user, monkeypatch):
        from apps.accounts import services as accounts_services
        monkeypatch.setattr(accounts_services, 'EMAIL_VERIFICATION_MAX_AGE_SECONDS', -1)
        token = generate_email_verification_token(staff_user)
        client = APIClient()
        response = client.post(VERIFY_CONFIRM_URL, {'token': token})
        assert response.status_code == 400
        assert 'expired' in response.data['detail'].lower()

    def test_confirm_stale_after_email_changed_again(self, staff_user):
        token = generate_email_verification_token(staff_user)
        staff_user.email = 'moved-on@ntc.example.com'
        staff_user.save(update_fields=['email'])

        client = APIClient()
        response = client.post(VERIFY_CONFIRM_URL, {'token': token})
        assert response.status_code == 400
        staff_user.refresh_from_db()
        assert staff_user.email_verified is False
