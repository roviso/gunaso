import pytest
from rest_framework.test import APIClient

from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db

ORGS_URL = '/api/v1/organizations/'


class TestOrganizationList:
    def test_anonymous_sees_only_verified_orgs(self, organization, citizen):
        Organization.objects.create(
            name='Unverified Org', slug='unverified-org',
            description='Not yet verified', category='other',
            contact_email='x@example.com', is_verified=False, admin=citizen,
        )
        response = APIClient().get(ORGS_URL)
        assert response.status_code == 200
        slugs = [o['slug'] for o in response.data['results']]
        assert 'nepal-telecom' in slugs
        assert 'unverified-org' not in slugs

    def test_admin_sees_own_unverified_org(self, citizen):
        Organization.objects.create(
            name='My Pending Org', slug='my-pending-org',
            description='Pending review', category='other',
            contact_email='mine@example.com', is_verified=False, admin=citizen,
        )
        client = APIClient()
        client.force_authenticate(citizen)
        slugs = [o['slug'] for o in client.get(ORGS_URL).data['results']]
        assert 'my-pending-org' in slugs


class TestOrganizationCreate:
    def test_requires_authentication(self):
        response = APIClient().post(ORGS_URL, {'name': 'X'})
        assert response.status_code == 401

    def test_create_upgrades_user_to_org_admin_and_generates_slug(self, citizen):
        client = APIClient()
        client.force_authenticate(citizen)
        response = client.post(ORGS_URL, {
            'name': 'Ward Office 5',
            'description': 'Local ward office serving the community.',
            'category': 'Government',
            'contact_email': 'ward5@example.com',
        })
        assert response.status_code == 201
        assert response.data['slug'] == 'ward-office-5'
        assert response.data['verified'] is False
        citizen.refresh_from_db()
        assert citizen.user_type == 'org_admin'

    def test_duplicate_name_rejected(self, organization, citizen):
        client = APIClient()
        client.force_authenticate(citizen)
        response = client.post(ORGS_URL, {
            'name': 'Nepal Telecom',
            'description': 'Impostor organization entry.',
            'category': 'telecom',
            'contact_email': 'fake@example.com',
        })
        assert response.status_code == 400


class TestOrgScopedEndpoints:
    def test_stats_denied_for_other_org_admin(self, organization, other_org_admin):
        client = APIClient()
        client.force_authenticate(other_org_admin)
        response = client.get(f'{ORGS_URL}{organization.slug}/stats/')
        assert response.status_code == 403

    def test_stats_allowed_for_own_admin(self, organization, org_admin, submission):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.get(f'{ORGS_URL}{organization.slug}/stats/')
        assert response.status_code == 200
        assert response.data['total'] == 1
        assert response.data['pending'] == 1

    def test_submissions_list_denied_for_non_admin(self, organization, citizen):
        client = APIClient()
        client.force_authenticate(citizen)
        response = client.get(f'{ORGS_URL}{organization.slug}/submissions/')
        assert response.status_code == 403


class TestOrganizationQRCode:
    def test_base64_payload_has_qr_code_data_uri(self, organization):
        response = APIClient().get(
            f'{ORGS_URL}{organization.slug}/qrcode/', {'format': 'base64'}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['qr_code'].startswith('data:image/png;base64,')
        assert data['url'].endswith(f'/submit/{organization.slug}')

    def test_origin_param_overrides_frontend_url(self, organization):
        response = APIClient().get(
            f'{ORGS_URL}{organization.slug}/qrcode/',
            {'format': 'base64', 'origin': 'https://example.ngrok-free.app'},
        )
        assert response.status_code == 200
        assert response.json()['url'] == (
            f'https://example.ngrok-free.app/submit/{organization.slug}'
        )

    def test_invalid_origin_falls_back_to_frontend_url(self, organization):
        response = APIClient().get(
            f'{ORGS_URL}{organization.slug}/qrcode/',
            {'format': 'base64', 'origin': 'javascript:alert(1)'},
        )
        assert response.status_code == 200
        assert response.json()['url'].startswith('http')
        assert 'javascript' not in response.json()['url']
