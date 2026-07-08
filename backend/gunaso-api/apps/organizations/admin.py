from django.contrib import admin
from .models import Organization, OrganizationStaff, Stakeholder


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


@admin.register(OrganizationStaff)
class OrganizationStaffAdmin(admin.ModelAdmin):
    list_display = ['user', 'organization', 'role', 'is_active', 'assigned_by', 'joined_at']
    list_filter = ['organization', 'role', 'is_active']
    search_fields = ['user__email', 'user__username', 'organization__name']
