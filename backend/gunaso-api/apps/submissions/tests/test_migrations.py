import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_legacy_notes_are_backfilled_as_internal():
    """Notes written before `kind` existed came from a composer labelled
    "not visible to citizen" — they must come out of the migration internal."""
    executor = MigrationExecutor(connection)
    leaves = executor.loader.graph.leaf_nodes()
    # Every other app stays at its latest state; only submissions steps back.
    before = [n for n in leaves if n[0] != 'submissions'] + [('submissions', '0005_submission_branch')]
    after = [n for n in leaves if n[0] != 'submissions'] + [('submissions', '0006_followup_and_satisfaction')]
    executor.migrate(before)
    old_apps = executor.loader.project_state(before).apps

    User = old_apps.get_model('accounts', 'User')
    Organization = old_apps.get_model('organizations', 'Organization')
    Submission = old_apps.get_model('submissions', 'Submission')
    StatusUpdate = old_apps.get_model('submissions', 'StatusUpdate')
    admin = User.objects.create(username='m', email='m@example.com')
    org = Organization.objects.create(name='O', slug='o', description='d', category='c',
                                      contact_email='o@example.com', admin=admin)
    sub = Submission.objects.create(reference_number='GUN-2026-77777', organization=org,
                                    title='t', description='d' * 30)
    StatusUpdate.objects.create(submission=sub, old_status='submitted', new_status='in_review')
    StatusUpdate.objects.create(submission=sub, old_status='in_review', new_status='in_review', note='private')

    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(after)
    new_apps = executor.loader.project_state(after).apps
    kinds = dict(new_apps.get_model('submissions', 'StatusUpdate').objects.values_list('note', 'kind'))
    assert kinds == {'': 'status_change', 'private': 'internal_note'}

    # Leave the schema at the latest state for the rest of the suite.
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())
