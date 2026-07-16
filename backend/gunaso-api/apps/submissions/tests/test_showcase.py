import pytest
from rest_framework.test import APIClient

from apps.organizations.models import OrganizationStaff, StaffRole
from apps.submissions.models import Submission

pytestmark = pytest.mark.django_db

ORGS_URL = '/api/v1/organizations/'
SUBMISSIONS_URL = '/api/v1/submissions/'


@pytest.fixture
def manage_submissions_role(organization):
    return StaffRole.objects.create(
        organization=organization, name='Case Handler', privileges=['manage_submissions'],
    )


@pytest.fixture
def no_manage_role(organization):
    return StaffRole.objects.create(
        organization=organization, name='Read Only', privileges=['view_submissions'],
    )


@pytest.fixture
def staff_user(django_user_model):
    return django_user_model.objects.create_user(
        username='casehandler', email='casehandler@ntc.example.com',
        password='Str0ng-pass-123', user_type='citizen',
    )


def make_staff(organization, user, role, status='active'):
    return OrganizationStaff.objects.create(organization=organization, user=user, role=role, status=status)


def visibility_url(submission):
    return f'{SUBMISSIONS_URL}{submission.reference_number}/visibility/'


def showcase_url(organization):
    return f'{ORGS_URL}{organization.slug}/showcase/'


class TestSubmissionVisibilityToggle:
    def test_org_admin_can_make_public(self, organization, org_admin, submission):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.patch(visibility_url(submission), {'is_public': True}, format='json')
        assert response.status_code == 200
        assert response.data['is_public'] is True
        submission.refresh_from_db()
        assert submission.is_public is True

    def test_staff_with_manage_submissions_can_toggle(
        self, organization, staff_user, manage_submissions_role, submission,
    ):
        make_staff(organization, staff_user, manage_submissions_role)
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.patch(visibility_url(submission), {'is_public': True}, format='json')
        assert response.status_code == 200

    def test_staff_without_manage_submissions_denied(
        self, organization, staff_user, no_manage_role, submission,
    ):
        make_staff(organization, staff_user, no_manage_role)
        client = APIClient()
        client.force_authenticate(staff_user)
        response = client.patch(visibility_url(submission), {'is_public': True}, format='json')
        assert response.status_code == 403
        submission.refresh_from_db()
        assert submission.is_public is False

    def test_can_toggle_back_to_private(self, organization, org_admin, submission):
        submission.is_public = True
        submission.save(update_fields=['is_public'])
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.patch(visibility_url(submission), {'is_public': False}, format='json')
        assert response.status_code == 200
        submission.refresh_from_db()
        assert submission.is_public is False

    def test_missing_is_public_rejected(self, organization, org_admin, submission):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.patch(visibility_url(submission), {}, format='json')
        assert response.status_code == 400

    def test_non_boolean_is_public_rejected(self, organization, org_admin, submission):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.patch(visibility_url(submission), {'is_public': 'yes'}, format='json')
        assert response.status_code == 400

    def test_regular_create_cannot_set_is_public(self, organization, org_admin):
        # is_public is read_only on SubmissionSerializer — a client can't sneak
        # it in through the normal create endpoint.
        client = APIClient()
        response = client.post(SUBMISSIONS_URL, {
            'organization': organization.id,
            'title': 'Water supply cut off for a week',
            'description': 'No water supply in our neighborhood for over a week now.',
            'is_anonymous': True,
            'is_public': True,
        })
        assert response.status_code == 201
        submission = Submission.objects.get(reference_number=response.data['reference_number'])
        assert submission.is_public is False


class TestOrganizationShowcase:
    def test_lists_only_public_submissions(self, organization, submission, anonymous_submission):
        submission.is_public = True
        submission.save(update_fields=['is_public'])
        # anonymous_submission stays private (is_public=False by default)

        client = APIClient()
        response = client.get(showcase_url(organization))
        assert response.status_code == 200
        refs = [s['reference_number'] for s in response.data['results']]
        assert submission.reference_number in refs
        assert anonymous_submission.reference_number not in refs

    def test_accessible_without_authentication(self, organization, submission):
        submission.is_public = True
        submission.save(update_fields=['is_public'])
        client = APIClient()
        client.credentials()
        response = client.get(showcase_url(organization))
        assert response.status_code == 200

    def test_public_submission_never_exposes_contact_details(self, organization, submission):
        submission.is_public = True
        submission.save(update_fields=['is_public'])
        client = APIClient()
        response = client.get(showcase_url(organization))
        row = response.data['results'][0]
        assert 'submitter_email' not in row
        assert 'submitter_phone' not in row

    def test_public_but_anonymous_submission_shows_anonymous_not_real_name(
        self, organization, anonymous_submission,
    ):
        anonymous_submission.is_public = True
        anonymous_submission.save(update_fields=['is_public'])
        client = APIClient()
        response = client.get(showcase_url(organization))
        row = response.data['results'][0]
        assert row['submitter_name'] == 'Anonymous'

    def test_public_non_anonymous_submission_shows_real_name(self, organization, submission):
        submission.is_public = True
        submission.save(update_fields=['is_public'])
        client = APIClient()
        response = client.get(showcase_url(organization))
        row = response.data['results'][0]
        assert row['submitter_name'] == submission.citizen_name

    def test_empty_when_nothing_public(self, organization, submission, anonymous_submission):
        client = APIClient()
        response = client.get(showcase_url(organization))
        assert response.status_code == 200
        assert response.data['results'] == []

    def test_showcase_reachable_even_for_unverified_org(self, other_organization, other_org_admin, submission):
        other_organization.is_verified = False
        other_organization.save(update_fields=['is_verified'])
        submission.organization = other_organization
        submission.is_public = True
        submission.save(update_fields=['organization', 'is_public'])

        client = APIClient()
        response = client.get(showcase_url(other_organization))
        assert response.status_code == 200
        refs = [s['reference_number'] for s in response.data['results']]
        assert submission.reference_number in refs

    def test_404_for_unknown_org_slug(self):
        client = APIClient()
        response = client.get(f'{ORGS_URL}does-not-exist/showcase/')
        assert response.status_code == 404
