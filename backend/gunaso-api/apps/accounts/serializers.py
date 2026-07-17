import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()

# user_type values a self-service registration may choose. 'stakeholder' and
# staff flags are only assignable by platform admins via the Django admin.
SELF_SERVICE_USER_TYPES = ('citizen', 'org_admin')


class UserSerializer(serializers.ModelSerializer):
    """Read/update serializer for the authenticated user's own profile."""

    name = serializers.SerializerMethodField()
    organization_name = serializers.SerializerMethodField()
    organization_slug = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'name',
            'user_type', 'phone', 'avatar', 'date_joined',
            'organization_name', 'organization_slug',
            'email_verified', 'must_change_password',
            'is_staff', 'is_superuser',
        ]
        read_only_fields = [
            'id', 'username', 'email', 'user_type', 'date_joined',
            'email_verified', 'must_change_password',
            'is_staff', 'is_superuser',
        ]

    def get_name(self, obj) -> str:
        return obj.get_full_name() or obj.username

    def _first_org(self, obj):
        return obj.managed_organizations.first() if obj.user_type == 'org_admin' else None

    def get_organization_name(self, obj) -> str | None:
        org = self._first_org(obj)
        return org.name if org else None

    def get_organization_slug(self, obj) -> str | None:
        org = self._first_org(obj)
        return org.slug if org else None

    # Design note (staff-roles-privileges subtask 05): `organization_name`/
    # `organization_slug` above answer one specific question — "does this
    # user *manage* an org as `org_admin`?" — and are left untouched here so
    # the existing org-admin frontend flow doesn't regress. A user's separate
    # *staff* relationship (an OrganizationStaff row with status='active',
    # possibly at a different organization, carrying its own role/privileges)
    # is deliberately NOT added to this serializer — conflating the two into
    # one payload would make it ambiguous which relationship a given field
    # describes for a user who is both an org_admin and staff elsewhere.
    # Instead it is exposed via a dedicated endpoint,
    # GET /api/v1/organizations/my-access/ (apps/organizations/views.py::MyStaffAccessView),
    # scoped to `request.user`'s own active membership only. See subtask 06
    # for the frontend consumption of that endpoint.


class ChangePasswordSerializer(serializers.Serializer):
    """Used both for the voluntary 'change my password' action and the forced
    first-login change on an admin-assigned account (User.must_change_password).
    Requires the current password even in the forced case — the user just
    typed it during login, but re-confirming it here still blocks a stolen
    access token (without the password) from silently rotating credentials."""

    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context['user']
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value

    def validate_new_password(self, value):
        validate_password(value, user=self.context['user'])
        return value


class UserRegistrationSerializer(serializers.Serializer):
    """
    Self-service registration. Accepts a display `name`, derives a unique
    username from the email, and enforces Django's password validators.
    """

    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    user_type = serializers.ChoiceField(choices=SELF_SERVICE_USER_TYPES, default='citizen')
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value

    def validate(self, attrs):
        temp_user = User(username=attrs['email'], email=attrs['email'])
        validate_password(attrs['password'], user=temp_user)
        return attrs

    def _unique_username(self, email: str) -> str:
        base = re.sub(r'[^a-z0-9_.]', '', email.split('@')[0].lower()) or 'user'
        username = base
        suffix = 1
        while User.objects.filter(username=username).exists():
            suffix += 1
            username = f'{base}{suffix}'
        return username

    def create(self, validated_data):
        name_parts = validated_data['name'].strip().split(' ', 1)
        user = User(
            username=self._unique_username(validated_data['email']),
            email=validated_data['email'],
            first_name=name_parts[0],
            last_name=name_parts[1] if len(name_parts) > 1 else '',
            user_type=validated_data['user_type'],
            phone=validated_data.get('phone', ''),
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class EmailVerificationRequestSerializer(serializers.Serializer):
    """Optionally corrects the account's email before sending a verification
    link to it — lets a staff member fix an admin-typo'd address in the same
    step as verifying it, without a separate 'edit profile' round trip."""

    email = serializers.EmailField(required=False)

    def validate_email(self, value):
        value = value.lower().strip()
        user = self.context['user']
        if User.objects.filter(email__iexact=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value
