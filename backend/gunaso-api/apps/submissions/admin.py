from django.contrib import admin
from .models import Category, Submission, StatusUpdate


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization']
    list_filter = ['organization']


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['reference_number', 'title', 'organization', 'submission_type', 'status', 'priority', 'created_at']
    list_filter = ['status', 'priority', 'submission_type', 'organization']
    search_fields = ['reference_number', 'title', 'citizen_email', 'citizen_name']
    readonly_fields = ['reference_number', 'created_at', 'updated_at']


@admin.register(StatusUpdate)
class StatusUpdateAdmin(admin.ModelAdmin):
    list_display = ['submission', 'updated_by', 'old_status', 'new_status', 'created_at']
    list_filter = ['new_status']
    readonly_fields = ['created_at']
