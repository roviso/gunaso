from django.contrib import admin
from .models import Organization, Stakeholder


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
