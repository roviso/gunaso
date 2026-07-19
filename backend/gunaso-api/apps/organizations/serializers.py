from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.text import slugify
from rest_framework import serializers

from .models import Branch, Organization, OrganizationStaff, Stakeholder, StaffRole
from .privileges import STAFF_PRIVILEGE_KEYS
from .services import generate_branch_code

User = get_user_model()


class BranchSerializer(serializers.ModelSerializer):
    """`organization` is never accepted from the client — it comes from
    `context['organization']`, which the view resolves (and permission-checks)
    from the URL slug, mirroring StaffRoleSerializer."""

    submission_count = serializers.SerializerMethodField()

    class Meta:
        model = Branch
        fields = [
            'id', 'organization', 'name', 'code', 'address',
            'latitude', 'longitude', 'is_active', 'submission_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'organization', 'code', 'created_at', 'updated_at']

    def get_submission_count(self, obj) -> int:
        count = getattr(obj, 'submission_count_annotated', None)
        return count if count is not None else obj.submissions.count()

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('This field may not be blank.')
        organization = self.context['organization']
        qs = Branch.objects.filter(organization=organization, name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A branch with this name already exists for this organization.')
        return value

    def create(self, validated_data):
        validated_data['organization'] = self.context['organization']
        validated_data['code'] = generate_branch_code()
        return Branch.objects.create(**validated_data)


class OrganizationSerializer(serializers.ModelSerializer):
    verified = serializers.BooleanField(source='is_verified', read_only=True)
    submission_count = serializers.SerializerMethodField()
    resolved_percent = serializers.SerializerMethodField()
    avg_resolution_days = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'slug', 'description', 'category',
            'logo', 'website', 'contact_email', 'contact_phone', 'address',
            'latitude', 'longitude', 'show_rating',
            'average_rating', 'rating_count',
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

    def get_average_rating(self, obj):
        if hasattr(obj, 'average_rating_annotated'):
            avg = obj.average_rating_annotated
        else:
            from django.db.models import Avg
            avg = obj.ratings.aggregate(avg=Avg('score'))['avg']
        return round(float(avg), 1) if avg is not None else None

    def get_rating_count(self, obj) -> int:
        count = getattr(obj, 'rating_count_annotated', None)
        return count if count is not None else obj.ratings.count()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # An org that opted out of public ratings still sees its own numbers
        # (its admin and platform staff do); everyone else gets null, mirroring
        # how HasOrgPrivilege treats admin/staff as implicit insiders.
        if not instance.show_rating and not self._can_see_hidden_rating(instance):
            data['average_rating'] = None
            data['rating_count'] = None
        return data

    def _can_see_hidden_rating(self, org) -> bool:
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        return bool(
            user and user.is_authenticated
            and (org.admin_id == user.id or user.is_staff)
        )

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


class StaffRoleSerializer(serializers.ModelSerializer):
    """A per-organization, admin-defined role.

    `organization` is never accepted from the client — it is always taken from
    `context['organization']`, which the view resolves from the URL slug (and
    has already permission-checked). This keeps role creation/editing scoped
    to the organization the caller is authorized for, never client-supplied.
    """

    staff_count = serializers.SerializerMethodField()

    class Meta:
        model = StaffRole
        fields = [
            'id', 'organization', 'name', 'privileges', 'staff_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'organization', 'created_at', 'updated_at']

    def get_staff_count(self, obj) -> int:
        count = getattr(obj, 'staff_count_annotated', None)
        return count if count is not None else obj.staff_members.count()

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('This field may not be blank.')
        organization = self.context['organization']
        qs = StaffRole.objects.filter(organization=organization, name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A role with this name already exists for this organization.')
        return value

    def validate_privileges(self, value):
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise serializers.ValidationError('Must be a list of privilege key strings.')
        unknown = sorted(set(value) - STAFF_PRIVILEGE_KEYS)
        if unknown:
            raise serializers.ValidationError(f'Unknown privilege key(s): {", ".join(unknown)}.')
        # De-duplicate while preserving the caller's ordering.
        deduped = []
        for key in value:
            if key not in deduped:
                deduped.append(key)
        return deduped

    def create(self, validated_data):
        validated_data['organization'] = self.context['organization']
        return StaffRole.objects.create(**validated_data)


class OrganizationStaffSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    assigned_by_name = serializers.SerializerMethodField()
    role_name = serializers.CharField(source='role.name', read_only=True)

    class Meta:
        model = OrganizationStaff
        fields = [
            'id', 'organization', 'user', 'user_email', 'user_name',
            'role', 'role_name', 'status', 'is_active', 'assigned_by', 'assigned_by_name', 'joined_at',
        ]
        # `status` moves invited -> active only through the invite-accept flow
        # (or resend/re-invite), never via a direct PATCH — see services.py.
        read_only_fields = ['id', 'organization', 'user', 'status', 'assigned_by', 'joined_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Scope the `role` choices to the organization this staff row belongs
        # to, so a role id from a different organization is rejected outright
        # rather than relying solely on `validate_role` below.
        organization = self.context.get('organization') or getattr(self.instance, 'organization', None)
        if organization is not None:
            self.fields['role'].queryset = StaffRole.objects.filter(organization=organization)

    def get_user_name(self, obj) -> str:
        return obj.user.get_full_name() or obj.user.username

    def get_assigned_by_name(self, obj):
        if obj.assigned_by:
            return obj.assigned_by.get_full_name() or obj.assigned_by.username
        return None

    def validate_role(self, value):
        organization = self.context.get('organization') or getattr(self.instance, 'organization', None)
        if organization is not None and value.organization_id != organization.id:
            raise serializers.ValidationError('This role does not belong to this organization.')
        return value


class OrganizationRatingSerializer(serializers.Serializer):
    """PUT /organizations/{slug}/rating/ body — score only, 1–5."""

    score = serializers.IntegerField(min_value=1, max_value=5)


class StaffInviteAcceptSerializer(serializers.Serializer):
    """POST /organizations/invite/<token>/accept/ body.

    The token itself is resolved by the view before this serializer runs
    (it needs the invitee's User to validate the password against, e.g. for
    UserAttributeSimilarityValidator) — the view passes it in via
    `context['user']`. Mirrors UserRegistrationSerializer.validate: raising
    Django's ValidationError from inside `validate()` is what lets DRF turn
    it into a normal 400 field_errors response instead of an unhandled 500.
    """

    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context['user']
        temp_user = User(
            username=user.username, email=user.email,
            first_name=user.first_name, last_name=user.last_name,
        )
        validate_password(attrs['password'], user=temp_user)
        return attrs
