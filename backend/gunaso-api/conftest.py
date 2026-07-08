import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    """Throttle counters live in the cache; reset them between tests."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def citizen(django_user_model):
    return django_user_model.objects.create_user(
        username='ram', email='ram@example.com', password='Str0ng-pass-123',
        first_name='Ram', last_name='Sharma', user_type='citizen',
    )


@pytest.fixture
def org_admin(django_user_model):
    return django_user_model.objects.create_user(
        username='orgadmin', email='admin@ntc.example.com', password='Str0ng-pass-123',
        first_name='Suresh', last_name='Pradhan', user_type='org_admin',
    )


@pytest.fixture
def other_org_admin(django_user_model):
    return django_user_model.objects.create_user(
        username='otheradmin', email='other@org.example.com', password='Str0ng-pass-123',
        user_type='org_admin',
    )


@pytest.fixture
def platform_staff(django_user_model):
    return django_user_model.objects.create_user(
        username='staffer', email='staff@gunaso.example.com', password='Str0ng-pass-123',
        is_staff=True,
    )


@pytest.fixture
def organization(org_admin):
    from apps.organizations.models import Organization
    return Organization.objects.create(
        name='Nepal Telecom', slug='nepal-telecom',
        description='Telecom provider', category='telecom',
        contact_email='support@ntc.example.com',
        is_verified=True, admin=org_admin,
    )


@pytest.fixture
def other_organization(other_org_admin):
    from apps.organizations.models import Organization
    return Organization.objects.create(
        name='Other Org', slug='other-org',
        description='Another org', category='government',
        contact_email='info@other.example.com',
        is_verified=True, admin=other_org_admin,
    )


@pytest.fixture
def submission(organization, citizen):
    from apps.submissions.models import Submission
    return Submission.objects.create(
        reference_number='GUN-2026-00001',
        organization=organization,
        citizen=citizen,
        citizen_name='Ram Sharma',
        citizen_email='ram@example.com',
        citizen_phone='9801234567',
        title='Internet down for three days',
        description='My fiber connection has been down for three days with no explanation.',
    )


@pytest.fixture
def anonymous_submission(organization):
    from apps.submissions.models import Submission
    return Submission.objects.create(
        reference_number='GUN-2026-00002',
        organization=organization,
        is_anonymous=True,
        title='Corruption in permit office',
        description='I want to report irregularities in the permit issuing process.',
    )
