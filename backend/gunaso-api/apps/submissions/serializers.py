from rest_framework import serializers

from .models import Category, StatusUpdate, Submission
from .services import create_submission
from .validators import validate_attachment


class CategorySerializer(serializers.ModelSerializer):
    organization_name = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'organization', 'organization_name']

    def get_organization_name(self, obj) -> str:
        return obj.organization.name if obj.organization else 'Global'


class TimelineEntrySerializer(serializers.ModelSerializer):
    """One entry in a submission's public timeline."""

    status = serializers.CharField(source='new_status', read_only=True)
    updated_by = serializers.SerializerMethodField()

    class Meta:
        model = StatusUpdate
        fields = ['status', 'note', 'created_at', 'updated_by']

    def get_updated_by(self, obj) -> str:
        if obj.updated_by:
            return obj.updated_by.get_full_name() or obj.updated_by.username
        return 'System'


class SubmissionSerializer(serializers.ModelSerializer):
    """
    Full submission serializer.

    Write contract (what the frontend sends):
        organization (id), type, category (name string), title, description,
        priority, attachment, is_anonymous, submitter_name/email/phone

    Read contract adds: reference_number, status, organization_name, org_slug,
    timeline. Submitter identity is redacted for anonymous submissions, and
    contact details are only shown to the org admin, the owner, or staff.
    """

    type = serializers.ChoiceField(
        source='submission_type', choices=Submission.TYPE_CHOICES, default='complaint'
    )
    category = serializers.CharField(
        max_length=100, required=False, allow_blank=True, write_only=True
    )
    submitter_name = serializers.CharField(
        source='citizen_name', max_length=200, required=False, allow_blank=True
    )
    submitter_email = serializers.EmailField(
        source='citizen_email', required=False, allow_blank=True
    )
    submitter_phone = serializers.CharField(
        source='citizen_phone', max_length=20, required=False, allow_blank=True
    )
    attachment = serializers.FileField(
        required=False, allow_null=True, validators=[validate_attachment]
    )
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    org_slug = serializers.CharField(source='organization.slug', read_only=True)
    timeline = TimelineEntrySerializer(source='updates', many=True, read_only=True)
    assigned_to = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = [
            'id', 'reference_number', 'organization', 'organization_name', 'org_slug',
            'type', 'category', 'title', 'description', 'attachment',
            'status', 'priority', 'is_anonymous', 'is_public', 'assigned_to',
            'submitter_name', 'submitter_email', 'submitter_phone',
            'created_at', 'updated_at', 'resolved_at', 'timeline',
        ]
        read_only_fields = [
            'id', 'reference_number', 'status', 'created_at', 'updated_at', 'resolved_at',
            # is_public is only ever changed via SubmissionVisibilityView
            # (privilege-gated) — never through a plain create/update.
            'is_public',
        ]
        extra_kwargs = {
            'title': {'min_length': 5},
            'description': {'min_length': 20},
        }

    def get_assigned_to(self, obj):
        if obj.assigned_to_id is None:
            return None
        staff = obj.assigned_to
        return {
            'id': staff.id,
            'user_name': staff.user.get_full_name() or staff.user.username,
            'role': staff.role.name if staff.role_id else None,
        }

    def validate(self, attrs):
        if not attrs.get('is_anonymous', False) and not self.instance:
            if not attrs.get('citizen_name', '').strip():
                raise serializers.ValidationError(
                    {'submitter_name': 'Name is required unless submitting anonymously.'}
                )
            if not attrs.get('citizen_email', '').strip():
                raise serializers.ValidationError(
                    {'submitter_email': 'Email is required unless submitting anonymously.'}
                )
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        organization = validated_data['organization']

        category_name = (validated_data.pop('category', '') or '').strip()
        if category_name:
            category = Category.objects.filter(
                name__iexact=category_name, organization=organization
            ).first() or Category.objects.filter(
                name__iexact=category_name, organization=None
            ).first()
            if category is None:
                category = Category.objects.create(name=category_name, organization=organization)
            validated_data['category'] = category

        citizen = None
        if request and request.user.is_authenticated and not validated_data.get('is_anonymous'):
            citizen = request.user
            if not validated_data.get('citizen_name'):
                validated_data['citizen_name'] = citizen.get_full_name() or citizen.username
            if not validated_data.get('citizen_email'):
                validated_data['citizen_email'] = citizen.email

        return create_submission(validated_data, citizen=citizen)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['category'] = instance.category.name if instance.category else None

        request = self.context.get('request')
        user = getattr(request, 'user', None)

        if instance.is_anonymous:
            # Identity is never revealed to organizations — only platform staff.
            if not (user and user.is_authenticated and user.is_staff):
                if 'submitter_name' in data:
                    data['submitter_name'] = 'Anonymous'
                if 'submitter_email' in data:
                    data['submitter_email'] = None
                if 'submitter_phone' in data:
                    data['submitter_phone'] = None
            return data

        is_privileged = bool(
            user
            and user.is_authenticated
            and (
                user.is_staff
                or instance.citizen_id == user.id
                or instance.organization.admin_id == user.id
            )
        )
        if not is_privileged:
            if 'submitter_email' in data:
                data['submitter_email'] = None
            if 'submitter_phone' in data:
                data['submitter_phone'] = None
        return data


class TrackSubmissionSerializer(SubmissionSerializer):
    """Public tracking view — never includes submitter contact details."""

    class Meta(SubmissionSerializer.Meta):
        fields = [
            'id', 'reference_number', 'organization', 'organization_name', 'org_slug',
            'type', 'category', 'title', 'description', 'attachment',
            'status', 'priority', 'is_anonymous', 'submitter_name',
            'created_at', 'updated_at', 'resolved_at', 'timeline',
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_anonymous:
            data['submitter_name'] = 'Anonymous'
        return data


class StatusUpdateSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = StatusUpdate
        fields = [
            'id', 'submission', 'updated_by', 'updated_by_name',
            'old_status', 'new_status', 'note', 'created_at',
        ]
        read_only_fields = [
            'id', 'submission', 'updated_by', 'updated_by_name',
            'old_status', 'new_status', 'created_at',
        ]

    def get_updated_by_name(self, obj) -> str:
        if obj.updated_by:
            return obj.updated_by.get_full_name() or obj.updated_by.username
        return 'System'
