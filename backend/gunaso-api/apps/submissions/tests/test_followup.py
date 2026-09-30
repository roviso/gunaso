"""Citizen follow-up: private keys, replies, outcome ratings, internal notes,
and lifecycle emails."""
import pytest
from django.core import mail
from rest_framework.test import APIClient

from apps.submissions.models import StatusUpdate, Submission
from apps.submissions.services import add_staff_note, issue_followup_key, transition_status

pytestmark = pytest.mark.django_db

SUBMISSIONS_URL = '/api/v1/submissions/'


def track_url(ref, action=''):
    return f'/api/v1/submissions/track/{ref}/{action + "/" if action else ""}'


@pytest.fixture(autouse=True)
def sync_notifications(settings):
    settings.NOTIFICATIONS_ASYNC = False


def create_via_api(organization, **overrides):
    payload = {
        'organization': organization.id,
        'description': 'The streetlight outside ward office has been broken for weeks.',
        'submitter_name': 'Gita Thapa',
        'submitter_email': 'gita@example.com',
        **overrides,
    }
    return APIClient().post(SUBMISSIONS_URL, payload)


class TestFollowUpKey:
    def test_create_response_carries_key_once_and_only_hash_is_stored(self, organization):
        response = create_via_api(organization)
        assert response.status_code == 201
        key = response.data['followup_key']
        assert len(key) >= 24

        submission = Submission.objects.get(reference_number=response.data['reference_number'])
        assert submission.followup_key_hash
        assert key not in submission.followup_key_hash

        track = APIClient().get(track_url(submission.reference_number))
        assert 'followup_key' not in track.data
        assert track.data['can_follow_up'] is False

    def test_track_with_key_header_grants_follow_up(self, organization):
        response = create_via_api(organization)
        ref, key = response.data['reference_number'], response.data['followup_key']
        track = APIClient().get(track_url(ref), HTTP_X_FOLLOWUP_KEY=key)
        assert track.data['can_follow_up'] is True

    def test_wrong_key_header_does_not_grant_follow_up(self, organization):
        ref = create_via_api(organization).data['reference_number']
        track = APIClient().get(track_url(ref), HTTP_X_FOLLOWUP_KEY='not-the-key')
        assert track.data['can_follow_up'] is False

    def test_signed_in_owner_can_follow_up_without_key(self, submission, citizen):
        client = APIClient()
        client.force_authenticate(citizen)
        assert client.get(track_url(submission.reference_number)).data['can_follow_up'] is True


class TestCitizenReply:
    def test_reply_with_key(self, organization):
        created = create_via_api(organization).data
        response = APIClient().post(
            track_url(created['reference_number'], 'reply'),
            {'key': created['followup_key'], 'message': 'It is still broken as of today.'},
        )
        assert response.status_code == 201
        last = response.data['timeline'][-1]
        assert last['kind'] == 'citizen_reply'
        assert last['note'] == 'It is still broken as of today.'
        assert last['updated_by'] == 'Gita Thapa'

    def test_reply_without_key_is_forbidden(self, submission):
        response = APIClient().post(track_url(submission.reference_number, 'reply'), {'message': 'hello there'})
        assert response.status_code == 403

    def test_reply_with_wrong_key_is_forbidden(self, submission):
        issue_followup_key(submission)
        response = APIClient().post(
            track_url(submission.reference_number, 'reply'), {'key': 'guess', 'message': 'hello there'},
        )
        assert response.status_code == 403

    def test_unknown_reference_looks_identical_to_wrong_key(self):
        response = APIClient().post(track_url('GUN-2026-99999', 'reply'), {'key': 'x', 'message': 'hello there'})
        assert response.status_code == 403

    def test_other_signed_in_user_cannot_reply_without_key(self, submission, org_admin):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(track_url(submission.reference_number, 'reply'), {'message': 'hello there'})
        assert response.status_code == 403

    def test_owner_reply_records_owner(self, submission, citizen):
        client = APIClient()
        client.force_authenticate(citizen)
        response = client.post(track_url(submission.reference_number, 'reply'), {'message': 'Any update?'})
        assert response.status_code == 201
        assert StatusUpdate.objects.get(kind='citizen_reply').updated_by == citizen

    def test_anonymous_reply_never_links_the_signed_in_account(self, anonymous_submission, citizen):
        """Someone signed in who holds the key of an anonymous case must not
        become its identifiable author."""
        key = issue_followup_key(anonymous_submission)
        client = APIClient()
        client.force_authenticate(citizen)
        response = client.post(
            track_url(anonymous_submission.reference_number, 'reply'), {'key': key, 'message': 'More details.'},
        )
        assert response.status_code == 201
        reply = StatusUpdate.objects.get(kind='citizen_reply')
        assert reply.updated_by is None
        assert response.data['timeline'][-1]['updated_by'] == 'Anonymous citizen'

    def test_closed_case_rejects_replies(self, submission, org_admin, citizen):
        for s in ('in_review', 'resolved', 'closed'):
            transition_status(submission, s, changed_by=org_admin)
        client = APIClient()
        client.force_authenticate(citizen)
        response = client.post(track_url(submission.reference_number, 'reply'), {'message': 'Reopen please'})
        assert response.status_code == 409

    def test_reply_marks_submission_awaiting_org(self, submission, citizen, org_admin):
        client = APIClient()
        client.force_authenticate(citizen)
        client.post(track_url(submission.reference_number, 'reply'), {'message': 'Any update?'})

        admin = APIClient()
        admin.force_authenticate(org_admin)
        data = admin.get('/api/v1/org/submissions/', {'awaiting_reply': 'true'}).data
        assert [s['reference_number'] for s in data['results']] == [submission.reference_number]
        assert data['results'][0]['awaiting_reply'] is True

        add_staff_note(submission, 'We are on it.', author=org_admin)
        data = admin.get('/api/v1/org/submissions/', {'awaiting_reply': 'true'}).data
        assert data['results'] == []

    def test_internal_note_does_not_answer_the_citizen(self, submission, citizen, org_admin):
        client = APIClient()
        client.force_authenticate(citizen)
        client.post(track_url(submission.reference_number, 'reply'), {'message': 'Any update?'})
        add_staff_note(submission, 'Check with field team', author=org_admin, internal=True)

        admin = APIClient()
        admin.force_authenticate(org_admin)
        data = admin.get('/api/v1/org/submissions/', {'awaiting_reply': 'true'}).data
        assert [s['reference_number'] for s in data['results']] == [submission.reference_number]


class TestSatisfaction:
    def _resolve(self, submission, org_admin):
        transition_status(submission, 'in_review', changed_by=org_admin)
        transition_status(submission, 'resolved', changed_by=org_admin)

    def test_rating_before_outcome_is_rejected(self, submission, citizen):
        client = APIClient()
        client.force_authenticate(citizen)
        response = client.post(track_url(submission.reference_number, 'feedback'), {'score': 5})
        assert response.status_code == 409

    def test_rating_after_resolution(self, submission, citizen, org_admin):
        self._resolve(submission, org_admin)
        client = APIClient()
        client.force_authenticate(citizen)
        response = client.post(
            track_url(submission.reference_number, 'feedback'), {'score': 4, 'comment': 'Fixed quickly'},
        )
        assert response.status_code == 200
        assert response.data['satisfaction_score'] == 4
        assert response.data['satisfaction_comment'] == 'Fixed quickly'

    def test_score_out_of_range(self, submission, citizen, org_admin):
        self._resolve(submission, org_admin)
        client = APIClient()
        client.force_authenticate(citizen)
        assert client.post(track_url(submission.reference_number, 'feedback'), {'score': 6}).status_code == 400
        assert client.post(track_url(submission.reference_number, 'feedback'), {'score': 0}).status_code == 400

    def test_stranger_cannot_rate(self, submission, org_admin):
        self._resolve(submission, org_admin)
        response = APIClient().post(track_url(submission.reference_number, 'feedback'), {'score': 1})
        assert response.status_code == 403

    def test_comment_is_private_to_the_submitter_on_public_track(self, submission, citizen, org_admin):
        self._resolve(submission, org_admin)
        client = APIClient()
        client.force_authenticate(citizen)
        client.post(track_url(submission.reference_number, 'feedback'), {'score': 2, 'comment': 'My phone is 98...'})

        public = APIClient().get(track_url(submission.reference_number)).data
        assert public['satisfaction_score'] == 2
        assert public['satisfaction_comment'] == ''

    def test_satisfaction_feeds_org_stats(self, submission, citizen, org_admin):
        self._resolve(submission, org_admin)
        client = APIClient()
        client.force_authenticate(citizen)
        client.post(track_url(submission.reference_number, 'feedback'), {'score': 4})

        admin = APIClient()
        admin.force_authenticate(org_admin)
        stats = admin.get('/api/v1/org/stats/').data
        assert stats['satisfaction_avg'] == 4.0
        assert stats['satisfaction_count'] == 1

    def test_satisfaction_is_not_writable_through_create(self, organization):
        response = create_via_api(organization, satisfaction_score=5)
        assert response.status_code == 201
        assert response.data['satisfaction_score'] is None


class TestInternalNotes:
    def test_org_admin_can_post_internal_note(self, submission, org_admin):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(
            f'{SUBMISSIONS_URL}{submission.reference_number}/updates/',
            {'note': 'Escalate to field team', 'internal': True}, format='json',
        )
        assert response.status_code == 201
        assert response.data['kind'] == 'internal_note'

    def test_internal_note_hidden_from_public_track_and_owner(self, submission, citizen, org_admin):
        add_staff_note(submission, 'Suspect fraud — keep quiet', author=org_admin, internal=True)
        add_staff_note(submission, 'We are looking into it', author=org_admin)

        public = APIClient().get(track_url(submission.reference_number)).data
        notes = [e['note'] for e in public['timeline']]
        assert 'We are looking into it' in notes
        assert 'Suspect fraud — keep quiet' not in notes

        owner = APIClient()
        owner.force_authenticate(citizen)
        for url in (f'{SUBMISSIONS_URL}{submission.reference_number}/', f'{SUBMISSIONS_URL}my/'):
            body = owner.get(url).data
            timeline = body['timeline'] if 'timeline' in body else body['results'][0]['timeline']
            assert 'Suspect fraud — keep quiet' not in [e['note'] for e in timeline]
        updates = owner.get(f'{SUBMISSIONS_URL}{submission.reference_number}/updates/').data
        assert 'Suspect fraud — keep quiet' not in [u['note'] for u in updates]

    def test_internal_note_visible_to_org(self, submission, org_admin):
        add_staff_note(submission, 'Suspect fraud — keep quiet', author=org_admin, internal=True)
        client = APIClient()
        client.force_authenticate(org_admin)
        timeline = client.get(f'{SUBMISSIONS_URL}{submission.reference_number}/').data['timeline']
        assert 'Suspect fraud — keep quiet' in [e['note'] for e in timeline]

    def test_citizen_cannot_post_staff_note(self, submission, citizen):
        client = APIClient()
        client.force_authenticate(citizen)
        response = client.post(f'{SUBMISSIONS_URL}{submission.reference_number}/updates/', {'note': 'hi'})
        assert response.status_code == 403

    def test_blank_note_rejected(self, submission, org_admin):
        client = APIClient()
        client.force_authenticate(org_admin)
        response = client.post(f'{SUBMISSIONS_URL}{submission.reference_number}/updates/', {'note': ''})
        assert response.status_code == 400


class TestNotifications:
    def test_receipt_email_with_private_link(self, organization, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            response = create_via_api(organization)
        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.to == ['gita@example.com']
        assert response.data['reference_number'] in email.subject
        assert f"#key={response.data['followup_key']}" in email.body

    def test_anonymous_submission_is_never_emailed(self, organization, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            create_via_api(organization, is_anonymous=True, submitter_email='')
        assert mail.outbox == []

    def test_anonymous_flag_wins_even_if_email_was_typed(self, organization, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            response = create_via_api(organization, is_anonymous=True)
        assert response.status_code == 201
        assert mail.outbox == []

    def test_status_change_emails_citizen(self, submission, org_admin, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            transition_status(submission, 'acknowledged', changed_by=org_admin, note='Technician assigned')
        assert len(mail.outbox) == 1
        assert 'Acknowledged' in mail.outbox[0].subject
        assert 'Technician assigned' in mail.outbox[0].body

    def test_public_reply_emails_but_internal_note_does_not(
        self, submission, org_admin, django_capture_on_commit_callbacks,
    ):
        with django_capture_on_commit_callbacks(execute=True):
            add_staff_note(submission, 'Internal only', author=org_admin, internal=True)
        assert mail.outbox == []
        with django_capture_on_commit_callbacks(execute=True):
            add_staff_note(submission, 'We replaced the cable', author=org_admin)
        assert len(mail.outbox) == 1
        assert 'We replaced the cable' in mail.outbox[0].body

    def test_email_failure_never_breaks_the_request(
        self, organization, settings, django_capture_on_commit_callbacks,
    ):
        settings.EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
        settings.EMAIL_HOST = '127.0.0.1'
        settings.EMAIL_PORT = 1  # nothing listens here
        settings.EMAIL_TIMEOUT = 1
        with django_capture_on_commit_callbacks(execute=True):
            response = create_via_api(organization)
        assert response.status_code == 201
