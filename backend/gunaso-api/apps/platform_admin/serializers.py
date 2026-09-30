from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.organizations.models import Organization

from .models import ContactMessage, PlatformAuditLog

User = get_user_model()


class AdminUserSerializer(serializers.ModelSerializer):
    """Read-only, cross-user view for the superadmin dashboard — every field
    the dashboard needs to search, filter, and act on any account."""

    name = serializers.SerializerMethodField()
    organization_name = serializers.SerializerMethodField()
    organization_slug = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'name', 'first_name', 'last_name',
            'user_type', 'phone', 'is_active', 'is_staff', 'is_superuser',
            'email_verified', 'date_joined', 'organization_name', 'organization_slug',
        ]
        read_only_fields = fields

    def get_name(self, obj) -> str:
        return obj.get_full_name() or obj.username

    def _managed_org(self, obj):
        return obj.managed_organizations.first() if obj.user_type == 'org_admin' else None

    def get_organization_name(self, obj) -> str | None:
        org = self._managed_org(obj)
        return org.name if org else None

    def get_organization_slug(self, obj) -> str | None:
        org = self._managed_org(obj)
        return org.slug if org else None


class AdminOrganizationSerializer(serializers.ModelSerializer):
    """Read-only dashboard view of an organization, verified or not.
    Mutations (verify, activate) go through the dedicated action endpoint —
    see AdminOrganizationActionView — never through a plain PATCH of this
    serializer's fields."""

    admin_name = serializers.SerializerMethodField()
    admin_email = serializers.CharField(source='admin.email', read_only=True)
    submission_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'slug', 'category', 'description', 'contact_email',
            'is_verified', 'is_active', 'admin', 'admin_name', 'admin_email',
            'submission_count', 'created_at',
        ]
        read_only_fields = fields

    def get_admin_name(self, obj) -> str:
        return obj.admin.get_full_name() or obj.admin.username

    def get_submission_count(self, obj) -> int:
        count = getattr(obj, 'submission_count_annotated', None)
        return count if count is not None else obj.submissions.count()


class PlatformAuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = PlatformAuditLog
        fields = [
            'id', 'actor', 'actor_name', 'action', 'target_type', 'target_id',
            'target_repr', 'note', 'created_at',
        ]
        read_only_fields = fields

    def get_actor_name(self, obj) -> str:
        if obj.actor:
            return obj.actor.get_full_name() or obj.actor.username
        return 'System'


class ContactMessageCreateSerializer(serializers.ModelSerializer):
    """Public contact form. `website` is a honeypot: humans never see the
    field, so any value means a bot (the view then drops the message while
    still answering 201, giving the bot nothing to learn from)."""

    website = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'organization', 'topic', 'message', 'website']
        extra_kwargs = {
            'name': {'max_length': 200},
            'message': {'min_length': 10, 'max_length': 5000},
        }


class ContactMessageSerializer(serializers.ModelSerializer):
    topic_label = serializers.CharField(source='get_topic_display', read_only=True)
    handled_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ContactMessage
        fields = [
            'id', 'name', 'email', 'organization', 'topic', 'topic_label', 'message',
            'is_handled', 'handled_by_name', 'handled_at', 'created_at',
        ]
        read_only_fields = fields

    def get_handled_by_name(self, obj):
        if obj.handled_by:
            return obj.handled_by.get_full_name() or obj.handled_by.username
        return None
