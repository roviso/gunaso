"""Public, unauthenticated surfaces: platform stats, showcased stories, the
map payload, the contact form, robots.txt and sitemap.xml."""
import pytest
from django.core import mail
from rest_framework.test import APIClient

from apps.organizations.models import Branch, Organization
from apps.platform_admin.models import ContactMessage
from apps.submissions.models import Submission

pytestmark = pytest.mark.django_db


@pytest.fixture
def unverified_org(other_org_admin):
    return Organization.objects.create(
        name='Shadow Org', slug='shadow-org', description='x', category='x',
        contact_email='x@example.com', is_verified=False, admin=other_org_admin,
    )


class TestPublicStats:
    def test_counts_only_verified_orgs(self, organization, unverified_org, submission):
        Submission.objects.create(
            reference_number='GUN-2026-00900', organization=unverified_org,
            title='Hidden', description='x' * 30,
        )
        Submission.objects.filter(pk=submission.pk).update(status='resolved')
        data = APIClient().get('/api/v1/public/stats/').data
        assert data['organizations'] == 1
        assert data['submissions'] == 1
        assert data['resolved'] == 1
        assert data['resolution_rate'] == 100

    def test_contains_no_content(self, submission):
        body = APIClient().get('/api/v1/public/stats/').content.decode()
        assert submission.title not in body
        assert submission.citizen_email not in body


class TestPublicStories:
    def test_only_showcased_from_verified_orgs(self, organization, unverified_org, submission, anonymous_submission):
        Submission.objects.filter(pk=anonymous_submission.pk).update(is_public=True)
        Submission.objects.create(
            reference_number='GUN-2026-00901', organization=unverified_org, is_public=True,
            title='Should not show', description='x' * 30,
        )
        data = APIClient().get('/api/v1/public/stories/').data
        assert [s['reference_number'] for s in data] == [anonymous_submission.reference_number]
        assert data[0]['submitter_name'] == 'Anonymous'
        assert 'submitter_email' not in data[0]


class TestLocations:
    def test_org_visible_through_branch_only(self, organization, unverified_org):
        Branch.objects.create(
            organization=organization, name='Kathmandu', code='LOC00001',
            latitude='27.700000', longitude='85.300000',
        )
        Branch.objects.create(
            organization=unverified_org, name='Shadow', code='LOC00002',
            latitude='27.700000', longitude='85.300000',
        )
        data = APIClient().get('/api/v1/organizations/locations/').data
        assert [o['slug'] for o in data] == [organization.slug]
        org = data[0]
        assert org['latitude'] is None
        assert org['branches'][0]['code'] == 'LOC00001'
        assert 'contact_email' not in org

    def test_org_without_any_location_is_excluded(self, organization):
        assert APIClient().get('/api/v1/organizations/locations/').data == []

    def test_stats_ride_along(self, organization, submission):
        Organization.objects.filter(pk=organization.pk).update(latitude='27.7', longitude='85.3')
        Submission.objects.filter(pk=submission.pk).update(status='resolved')
        org = APIClient().get('/api/v1/organizations/locations/').data[0]
        assert org['submission_count'] == 1
        assert org['resolved_percent'] == 100


class TestContactForm:
    VALID = {
        'name': 'Sita Rai', 'email': 'sita@example.com', 'topic': 'organization',
        'organization': 'Ward 4 Office', 'message': 'We would like to onboard our ward office.',
    }

    def test_public_submit(self):
        response = APIClient().post('/api/v1/contact/', self.VALID)
        assert response.status_code == 201
        assert ContactMessage.objects.get().organization == 'Ward 4 Office'

    def test_honeypot_is_silently_dropped(self):
        response = APIClient().post('/api/v1/contact/', {**self.VALID, 'website': 'http://spam'})
        assert response.status_code == 201
        assert ContactMessage.objects.count() == 0

    def test_validation(self):
        response = APIClient().post('/api/v1/contact/', {**self.VALID, 'email': 'nope', 'message': 'hi'})
        assert response.status_code == 400
        assert set(response.data['error']['field_errors']) >= {'email', 'message'}

    def test_forwarded_when_configured(self, settings, django_capture_on_commit_callbacks):
        settings.CONTACT_NOTIFY_EMAIL = 'team@gunaso.example.com'
        with django_capture_on_commit_callbacks(execute=True):
            APIClient().post('/api/v1/contact/', self.VALID)
        assert mail.outbox[0].to == ['team@gunaso.example.com']
        assert mail.outbox[0].reply_to == ['sita@example.com']

    def test_throttled(self, settings):
        client = APIClient()
        codes = [client.post('/api/v1/contact/', self.VALID).status_code for _ in range(7)]
        assert codes[-1] == 429

    def test_inbox_is_superadmin_only(self, platform_staff, citizen, django_user_model):
        ContactMessage.objects.create(name='a', email='a@example.com', message='hello there friend')
        for user in (citizen, platform_staff):
            client = APIClient()
            client.force_authenticate(user)
            assert client.get('/api/v1/admin/contact-messages/').status_code == 403

        superadmin = django_user_model.objects.create_user(
            username='root', email='root@example.com', password='Str0ng-pass-123',
            is_staff=True, is_superuser=True,
        )
        client = APIClient()
        client.force_authenticate(superadmin)
        listing = client.get('/api/v1/admin/contact-messages/')
        assert listing.status_code == 200
        message_id = listing.data['results'][0]['id']
        patched = client.patch(
            f'/api/v1/admin/contact-messages/{message_id}/', {'is_handled': True}, format='json',
        )
        assert patched.status_code == 200
        assert patched.data['is_handled'] is True
        assert patched.data['handled_by_name'] == 'root'
        assert client.get('/api/v1/admin/overview/').data['inbox']['unhandled'] == 0


class TestSeo:
    def test_robots(self, client):
        response = client.get('/robots.txt')
        assert response.status_code == 200
        assert 'Sitemap:' in response.content.decode()
        assert 'Disallow: /api/' in response.content.decode()

    def test_sitemap_lists_only_verified_orgs(self, client, organization, unverified_org):
        body = client.get('/sitemap.xml').content.decode()
        assert f'/organizations/{organization.slug}' in body
        assert unverified_org.slug not in body
