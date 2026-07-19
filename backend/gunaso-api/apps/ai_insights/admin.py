from django.contrib import admin

from .models import AIReport, AISuggestion, SubmissionInsight


class ReadOnlyGeneratedAdmin(admin.ModelAdmin):
    """Shared behavior for AI-generated, never-hand-authored records."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SubmissionInsight)
class SubmissionInsightAdmin(ReadOnlyGeneratedAdmin):
    list_display = ['submission', 'suggested_category', 'confidence', 'sentiment', 'applied', 'updated_at']
    list_filter = ['sentiment', 'applied']
    search_fields = ['submission__reference_number', 'suggested_category']
    readonly_fields = [f.name for f in SubmissionInsight._meta.fields]


@admin.register(AISuggestion)
class AISuggestionAdmin(ReadOnlyGeneratedAdmin):
    list_display = ['submission', 'updated_at']
    search_fields = ['submission__reference_number']
    readonly_fields = [f.name for f in AISuggestion._meta.fields]


@admin.register(AIReport)
class AIReportAdmin(ReadOnlyGeneratedAdmin):
    list_display = ['organization', 'date_from', 'date_to', 'submission_count', 'created_by', 'created_at']
    list_filter = ['organization']
    search_fields = ['organization__name']
    readonly_fields = [f.name for f in AIReport._meta.fields]
