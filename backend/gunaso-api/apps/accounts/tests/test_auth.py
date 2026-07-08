import pytest
from django.conf import settings
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

REGISTER_URL = '/api/v1/auth/register/'
LOGIN_URL = '/api/v1/auth/login/'
REFRESH_URL = '/api/v1/auth/refresh/'
LOGOUT_URL = '/api/v1/auth/logout/'
ME_URL = '/api/v1/auth/me/'


class TestRegistration:
    def test_register_returns_access_token_user_and_refresh_cookie(self):
        client = APIClient()
        response = client.post(REGISTER_URL, {
            'name': 'Sita Rai',
            'email': 'sita@example.com',
            'password': 'Str0ng-pass-123',
            'user_type': 'citizen',
        })
        assert response.status_code == 201
        assert 'access' in response.data
        assert response.data['user']['email'] == 'sita@example.com'
        assert response.data['user']['name'] == 'Sita Rai'
        assert settings.JWT_REFRESH_COOKIE in response.cookies
        assert response.cookies[settings.JWT_REFRESH_COOKIE]['httponly']

    def test_register_rejects_duplicate_email(self, citizen):
        client = APIClient()
        response = client.post(REGISTER_URL, {
            'name': 'Copy Cat',
            'email': citizen.email,
            'password': 'Str0ng-pass-123',
        })
        assert response.status_code == 400
        assert 'email' in response.data['error']['field_errors']

    def test_register_rejects_weak_password(self):
        client = APIClient()
        response = client.post(REGISTER_URL, {
            'name': 'Weak Pass',
            'email': 'weak@example.com',
            'password': 'password',
        })
        assert response.status_code == 400

    def test_register_rejects_privileged_user_type(self):
        client = APIClient()
        response = client.post(REGISTER_URL, {
            'name': 'Sneaky',
            'email': 'sneaky@example.com',
            'password': 'Str0ng-pass-123',
            'user_type': 'stakeholder',
        })
        assert response.status_code == 400


class TestLogin:
    def test_login_with_email_succeeds(self, citizen):
        client = APIClient()
        response = client.post(LOGIN_URL, {'email': citizen.email, 'password': 'Str0ng-pass-123'})
        assert response.status_code == 200
        assert 'access' in response.data
        assert 'refresh' not in response.data  # refresh only travels in the cookie
        assert response.data['user']['email'] == citizen.email
        assert settings.JWT_REFRESH_COOKIE in response.cookies

    def test_login_wrong_password_and_unknown_email_return_same_message(self, citizen):
        client = APIClient()
        wrong_pass = client.post(LOGIN_URL, {'email': citizen.email, 'password': 'nope'})
        unknown = client.post(LOGIN_URL, {'email': 'ghost@example.com', 'password': 'nope'})
        assert wrong_pass.status_code == unknown.status_code == 401
        assert wrong_pass.data['error']['message'] == unknown.data['error']['message']


class TestRefreshAndLogout:
    def test_refresh_rotates_cookie_and_returns_new_access(self, citizen):
        client = APIClient()
        login = client.post(LOGIN_URL, {'email': citizen.email, 'password': 'Str0ng-pass-123'})
        old_cookie = login.cookies[settings.JWT_REFRESH_COOKIE].value

        response = client.post(REFRESH_URL)
        assert response.status_code == 200
        assert 'access' in response.data
        assert response.cookies[settings.JWT_REFRESH_COOKIE].value != old_cookie

        # The old (rotated-out) refresh token must be blacklisted.
        client.cookies[settings.JWT_REFRESH_COOKIE] = old_cookie
        replay = client.post(REFRESH_URL)
        assert replay.status_code == 401

    def test_logout_blacklists_refresh_token(self, citizen):
        client = APIClient()
        client.post(LOGIN_URL, {'email': citizen.email, 'password': 'Str0ng-pass-123'})
        cookie = client.cookies[settings.JWT_REFRESH_COOKIE].value

        assert client.post(LOGOUT_URL).status_code == 200

        client.cookies[settings.JWT_REFRESH_COOKIE] = cookie
        assert client.post(REFRESH_URL).status_code == 401


class TestMe:
    def test_me_requires_authentication(self):
        assert APIClient().get(ME_URL).status_code == 401

    def test_me_returns_profile(self, citizen):
        client = APIClient()
        client.force_authenticate(citizen)
        response = client.get(ME_URL)
        assert response.status_code == 200
        assert response.data['email'] == citizen.email
        assert response.data['user_type'] == 'citizen'
