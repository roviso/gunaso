from django.core.management.base import BaseCommand, CommandError

from apps.ai_insights.client import AIError
from apps.ai_insights.services import classify_and_store, is_ai_enabled
from apps.submissions.models import Submission


class Command(BaseCommand):
    help = "Batch-run AI classification for submissions that don't have an insight yet."

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=50, help='Max submissions to classify in this run.')
        parser.add_argument('--org', type=str, default=None, help='Only classify submissions for this organization slug.')

    def handle(self, *args, **options):
        if not is_ai_enabled():
            raise CommandError('ANTHROPIC_API_KEY is not configured — AI features are disabled.')

        queryset = Submission.objects.filter(ai_insight__isnull=True).select_related('organization')
        org_slug = options['org']
        if org_slug:
            queryset = queryset.filter(organization__slug=org_slug)
        queryset = queryset.order_by('-created_at')[:options['limit']]

        classified = 0
        for submission in queryset:
            try:
                _insight, applied = classify_and_store(submission)
            except AIError as exc:
                self.stderr.write(self.style.WARNING(f'{submission.reference_number}: {exc}'))
                continue
            classified += 1
            note = ' (category auto-applied)' if applied else ''
            self.stdout.write(f'{submission.reference_number}: classified{note}')

        self.stdout.write(self.style.SUCCESS(f'Classified {classified} submission(s).'))
