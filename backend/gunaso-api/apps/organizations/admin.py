from django.contrib import admin
from .models import Organization, OrganizationRating, OrganizationStaff, Stakeholder, StaffInvite, StaffRole


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_verified', 'admin', 'created_at']
    list_filter = ['is_verified', 'category']
    search_fields = ['name', 'contact_email']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Stakeholder)
class StakeholderAdmin(admin.ModelAdmin):
    list_display = ['user', 'organization', 'role', 'receives_all']
    list_filter = ['organization', 'receives_all']


@admin.register(StaffRole)
class StaffRoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'created_at', 'updated_at']
    list_filter = ['organization']
    search_fields = ['name', 'organization__name']


@admin.register(OrganizationStaff)
class OrganizationStaffAdmin(admin.ModelAdmin):
    list_display = ['user', 'organization', 'role', 'status', 'is_active', 'assigned_by', 'joined_at']
    list_filter = ['organization', 'role', 'status', 'is_active']
    search_fields = ['user__email', 'user__username', 'organization__name']


@admin.register(OrganizationRating)
class OrganizationRatingAdmin(admin.ModelAdmin):
    """Ratings belong to citizens — platform staff may inspect or remove abuse,
    but never author/alter scores on a user's behalf."""

    list_display = ['organization', 'user', 'score', 'created_at', 'updated_at']
    list_filter = ['score', 'organization']
    search_fields = ['organization__name', 'user__email', 'user__username']
    readonly_fields = ['organization', 'user', 'score', 'created_at', 'updated_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(StaffInvite)
class StaffInviteAdmin(admin.ModelAdmin):
    """Append-only, like StatusUpdate: invites are never edited or deleted via admin."""

    list_display = ['staff', 'expires_at', 'accepted_at', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['staff__user__email', 'staff__organization__name']
    readonly_fields = ['token_hash', 'expires_at', 'accepted_at']

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
