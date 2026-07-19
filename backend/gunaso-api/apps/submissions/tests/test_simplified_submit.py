import pytest
from rest_framework.test import APIClient

from apps.submissions.models import Submission
from apps.submissions.services import derive_title

pytestmark = pytest.mark.django_db

SUBMISSIONS_URL = '/api/v1/submissions/'


# --- derive_title() unit tests ---------------------------------------------

class TestDeriveTitle:
    def test_short_description_used_verbatim(self):
        assert derive_title('Water leaking near the office entrance') == \
            'Water leaking near the office entrance'

    def test_truncates_long_description_at_word_boundary(self):
        text = 'This is a very long gunaso description that goes on and on well past sixty characters total'
        title = derive_title(text)
        assert title.endswith('…')
        assert len(title) <= 61  # 60 + ellipsis
        assert not title[:-1].endswith(' ')  # trimmed at a word boundary, no trailing space before the ellipsis

    def test_stops_at_first_sentence(self):
        assert derive_title('Water is leaking. It has been three days now.') == 'Water is leaking'

    def test_stops_at_nepali_danda(self):
        assert derive_title('पानी चुहिरहेको छ। तीन दिन भइसक्यो।') == 'पानी चुहिरहेको छ'

    def test_blank_description_gets_placeholder(self):
        assert derive_title('') == 'Gunaso'
        assert derive_title('   ') == 'Gunaso'

    def test_collapses_internal_whitespace(self):
        assert derive_title('Water   leaking\n\nnear   entrance') == 'Water leaking near entrance'


# --- API: title omitted ------------------------------------------------------

class TestOptionalTitleOnSubmit:
    def _payload(self, organization, **overrides):
        payload = {
            'organization': organization.id,
            'type': 'complaint',
            'description': 'The water supply has been irregular for the past two weeks.',
            'is_anonymous': True,
        }
        payload.update(overrides)
        return payload

    def test_submission_without_title_succeeds(self, organization):
        response = APIClient().post(SUBMISSIONS_URL, self._payload(organization))
        assert response.status_code == 201
        assert response.data['title']  # server derived a non-empty title
        submission = Submission.objects.get(reference_number=response.data['reference_number'])
        assert submission.title == derive_title(self._payload(organization)['description'])

    def test_submission_with_blank_title_succeeds(self, organization):
        response = APIClient().post(SUBMISSIONS_URL, self._payload(organization, title=''))
        assert response.status_code == 201
        assert response.data['title']

    def test_submission_without_category_succeeds(self, organization):
        response = APIClient().post(SUBMISSIONS_URL, self._payload(organization))
        assert response.status_code == 201
        assert response.data['category'] is None

    def test_explicit_short_title_still_rejected(self, organization):
        response = APIClient().post(SUBMISSIONS_URL, self._payload(organization, title='Hi'))
        assert response.status_code == 400
        assert 'title' in response.data['error']['field_errors']

    def test_explicit_valid_title_is_kept_verbatim(self, organization):
        response = APIClient().post(
            SUBMISSIONS_URL, self._payload(organization, title='Custom title here'),
        )
        assert response.status_code == 201
        assert response.data['title'] == 'Custom title here'

    def test_description_still_required(self, organization):
        payload = self._payload(organization)
        payload.pop('description')
        response = APIClient().post(SUBMISSIONS_URL, payload)
        assert response.status_code == 400
        assert 'description' in response.data['error']['field_errors']
