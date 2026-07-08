from django.utils.text import slugify
from rest_framework import serializers

from .models import Organization, OrganizationStaff, Stakeholder


class OrganizationSerializer(serializers.ModelSerializer):
    verified = serializers.BooleanField(source='is_verified', read_only=True)
    submission_count = serializers.SerializerMethodField()
    resolved_percent = serializers.SerializerMethodField()
    avg_resolution_days = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'slug', 'description', 'category',
            'logo', 'website', 'contact_email', 'contact_phone', 'address',
            'verified', 'is_verified', 'submission_count',
            'resolved_percent', 'avg_resolution_days', 'created_at',
        ]
        read_only_fields = ['id', 'slug', 'is_verified', 'created_at']

    def get_submission_count(self, obj) -> int:
        # Prefer the annotated value from the view queryset; fall back to a count query.
        count = getattr(obj, 'submission_count_annotated', None)
        return count if count is not None else obj.submissions.count()

    def get_resolved_percent(self, obj) -> int:
        total = self.get_submission_count(obj)
        if not total:
            return 0
        resolved = getattr(obj, 'resolved_count_annotated', None)
        if resolved is None:
            resolved = obj.submissions.filter(status__in=['resolved', 'closed']).count()
        return round(resolved * 100 / total)

    def get_avg_resolution_days(self, obj) -> float:
        avg = getattr(obj, 'avg_resolution_annotated', None)
        return round(avg.total_seconds() / 86400, 1) if avg else 0

    def validate_name(self, value):
        qs = Organization.objects.filter(name__iexact=value.strip())
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('An organization with this name is already registered.')
        return value.strip()

    def _unique_slug(self, name: str) -> str:
        base = slugify(name) or 'organization'
        slug = base
        suffix = 1
        while Organization.objects.filter(slug=slug).exists():
            suffix += 1
            slug = f'{base}-{suffix}'
        return slug

    def create(self, validated_data):
        request = self.context['request']
        validated_data['slug'] = self._unique_slug(validated_data['name'])
        org = Organization.objects.create(admin=request.user, **validated_data)
        # Whoever registers an organization manages it.
        if request.user.user_type != 'org_admin':
            request.user.user_type = 'org_admin'
            request.user.save(update_fields=['user_type'])
        return org


class StakeholderSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Stakeholder
        fields = ['id', 'organization', 'user', 'user_name', 'role', 'receives_all']

    def get_user_name(self, obj) -> str:
        return obj.user.get_full_name() or obj.user.username


class OrganizationStaffSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    assigned_by_name = serializers.SerializerMethodField()

    class Meta:
        model = OrganizationStaff
        fields = [
            'id', 'organization', 'user', 'user_email', 'user_name',
            'role', 'is_active', 'assigned_by', 'assigned_by_name', 'joined_at',
        ]
        read_only_fields = ['id', 'organization', 'user', 'assigned_by', 'joined_at']

    def get_user_name(self, obj) -> str:
        return obj.user.get_full_name() or obj.user.username

    def get_assigned_by_name(self, obj):
        if obj.assigned_by:
            return obj.assigned_by.get_full_name() or obj.assigned_by.username
        return None
