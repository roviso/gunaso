from django.contrib import admin

from .models import PlatformAuditLog


@admin.register(PlatformAuditLog)
class PlatformAuditLogAdmin(admin.ModelAdmin):
    """Append-only, like StatusUpdate/StaffInvite: entries are never edited or deleted via admin."""

    list_display = ['action', 'target_type', 'target_repr', 'actor', 'created_at']
    list_filter = ['action', 'target_type']
    search_fields = ['target_repr', 'actor__email', 'actor__username']
    readonly_fields = ['actor', 'action', 'target_type', 'target_id', 'target_repr', 'note', 'created_at']

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
