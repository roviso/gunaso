import pytest
from rest_framework.test import APIClient

from apps.organizations.models import Organization, OrganizationRating

pytestmark = pytest.mark.django_db

ORGS_URL = '/api/v1/organizations/'


def rating_url(org):
    return f'{ORGS_URL}{org.slug}/rating/'


@pytest.fixture
def second_citizen(django_user_model):
    return django_user_model.objects.create_user(
        username='sita', email='sita@example.com', password='Str0ng-pass-123',
        first_name='Sita', last_name='Rai', user_type='citizen',
    )


class TestRateOrganization:
    def test_guest_cannot_rate(self, organization):
        response = APIClient().put(rating_url(organization), {'score': 4})
        assert response.status_code == 401

    def test_citizen_can_rate(self, organization, citizen):
        client = APIClient()
        client.force_authenticate(citizen)
        response = client.put(rating_url(organization), {'score': 4})
        assert response.status_code == 200
        assert response.data['score'] == 4
        assert OrganizationRating.objects.filter(organization=organization, user=citizen).count() == 1

    def test_rerating_updates_instead_of_duplicating(self, organization, citizen):
        client = APIClient()
        client.force_authenticate(citizen)
        client.put(rating_url(organization), {'score': 2})
        response = client.put(rating_url(organization), {'score': 5})
        assert response.status_code == 200
        ratings = OrganizationRating.objects.filter(organization=organization, user=citizen)
        assert ratings.count() == 1
        assert ratings.first().score == 5

    @pytest.mark.parametrize('score', [0, 6, -1, 'five'])
    def test_invalid_score_rejected(self, organization, citizen, score):
        client = APIClient()
        client.force_authenticate(citizen)
        response = client.put(rating_url(organization), {'score': score})
        assert response.status_code == 400

    def test_get_own_rating_and_null_when_unrated(self, organization, citizen):
        client = APIClient()
        client.force_authenticate(citizen)
        assert client.get(rating_url(organization)).data['score'] is None
        client.put(rating_url(organization), {'score': 3})
        assert client.get(rating_url(organization)).data['score'] == 3

    def test_delete_withdraws_rating(self, organization, citizen):
        client = APIClient()
        client.force_authenticate(citizen)
        client.put(rating_url(organization), {'score': 3})
        response = client.delete(rating_url(organization))
        assert response.status_code == 204
        assert not OrganizationRating.objects.filter(organization=organization, user=citizen).exists()

    def test_unknown_org_404(self, citizen):
        client = APIClient()
        client.force_authenticate(citizen)
        response = client.put(f'{ORGS_URL}nope/rating/', {'score': 3})
        assert response.status_code == 404


class TestAverageRatingVisibility:
    def _rate(self, org, user, score):
        OrganizationRating.objects.create(organization=org, user=user, score=score)

    def test_public_detail_includes_average(self, organization, citizen, second_citizen):
        self._rate(organization, citizen, 4)
        self._rate(organization, second_citizen, 5)
        response = APIClient().get(f'{ORGS_URL}{organization.slug}/')
        assert response.status_code == 200
        assert response.data['average_rating'] == 4.5
        assert response.data['rating_count'] == 2

    def test_no_ratings_yields_null_average(self, organization):
        response = APIClient().get(f'{ORGS_URL}{organization.slug}/')
        assert response.data['average_rating'] is None
        assert response.data['rating_count'] == 0

    def test_hidden_when_org_opts_out(self, organization, citizen):
        self._rate(organization, citizen, 2)
        organization.show_rating = False
        organization.save(update_fields=['show_rating'])
        response = APIClient().get(f'{ORGS_URL}{organization.slug}/')
        assert response.data['average_rating'] is None
        assert response.data['rating_count'] is None

    def test_hidden_from_other_authenticated_users(self, organization, citizen, second_citizen):
        self._rate(organization, citizen, 2)
        organization.show_rating = False
        organization.save(update_fields=['show_rating'])
        client = APIClient()
        client.force_authenticate(second_citizen)
        response = client.get(f'{ORGS_URL}{organization.slug}/')
        assert response.data['average_rating'] is None

    def test_own_admin_still_sees_hidden_average(self, organization, org_admin, citizen):
        self._rate(organization, citizen, 2)
        organization.show_rating = False
        organization.save(update_fields=['show_rating'])
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.get(f'{ORGS_URL}mine/')
        assert response.status_code == 200
        assert response.data['average_rating'] == 2.0
        assert response.data['rating_count'] == 1

    def test_platform_staff_sees_hidden_average(self, organization, platform_staff, citizen):
        self._rate(organization, citizen, 2)
        organization.show_rating = False
        organization.save(update_fields=['show_rating'])
        client = APIClient()
        client.force_authenticate(platform_staff)
        response = client.get(f'{ORGS_URL}{organization.slug}/')
        assert response.data['average_rating'] == 2.0


class TestOrganizationLocations:
    LOCATIONS_URL = f'{ORGS_URL}locations/'

    def _locate(self, org, lat='27.700000', lng='85.300000'):
        org.latitude = lat
        org.longitude = lng
        org.save(update_fields=['latitude', 'longitude'])

    def test_public_and_only_orgs_with_coordinates(self, organization, other_organization):
        self._locate(organization)
        response = APIClient().get(self.LOCATIONS_URL)
        assert response.status_code == 200
        slugs = [o['slug'] for o in response.data]
        assert organization.slug in slugs
        assert other_organization.slug not in slugs  # no coordinates set

    def test_unverified_org_excluded(self, citizen):
        org = Organization.objects.create(
            name='Hidden Org', slug='hidden-org', description='x', category='other',
            contact_email='x@example.com', is_verified=False, admin=citizen,
            latitude='27.7', longitude='85.3',
        )
        slugs = [o['slug'] for o in APIClient().get(self.LOCATIONS_URL).data]
        assert org.slug not in slugs

    def test_payload_includes_rating_when_public(self, organization, citizen):
        self._locate(organization)
        OrganizationRating.objects.create(organization=organization, user=citizen, score=5)
        entry = APIClient().get(self.LOCATIONS_URL).data[0]
        assert entry['average_rating'] == 5.0
        assert entry['rating_count'] == 1
        assert entry['latitude'] == pytest.approx(27.7)
        assert entry['longitude'] == pytest.approx(85.3)

    def test_rating_nulled_when_org_opts_out(self, organization, citizen):
        self._locate(organization)
        OrganizationRating.objects.create(organization=organization, user=citizen, score=5)
        organization.show_rating = False
        organization.save(update_fields=['show_rating'])
        entry = APIClient().get(self.LOCATIONS_URL).data[0]
        assert entry['average_rating'] is None
        assert entry['rating_count'] is None


class TestSettingsNewFields:
    def test_admin_can_update_location_and_rating_visibility(self, organization, org_admin):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.patch(f'{ORGS_URL}{organization.slug}/settings/', {
            'latitude': '27.717245', 'longitude': '85.323959', 'show_rating': False,
        })
        assert response.status_code == 200
        organization.refresh_from_db()
        assert float(organization.latitude) == pytest.approx(27.717245)
        assert float(organization.longitude) == pytest.approx(85.323959)
        assert organization.show_rating is False

    @pytest.mark.parametrize('field,value', [
        ('latitude', '91'), ('latitude', '-91'),
        ('longitude', '181'), ('longitude', '-181'),
    ])
    def test_out_of_range_coordinates_rejected(self, organization, org_admin, field, value):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.patch(f'{ORGS_URL}{organization.slug}/settings/', {field: value})
        assert response.status_code == 400

    def test_other_org_admin_cannot_update(self, organization, other_org_admin):
        client = APIClient()
        client.force_authenticate(other_org_admin)
        response = client.patch(f'{ORGS_URL}{organization.slug}/settings/', {'show_rating': False})
        assert response.status_code == 403
