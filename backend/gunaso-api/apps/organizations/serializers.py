from django.utils.text import slugify
from rest_framework import serializers
from .models import Organization, Stakeholder


class OrganizationSerializer(serializers.ModelSerializer):
    admin_name = serializers.SerializerMethodField()
    submission_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'slug', 'description', 'category',
            'logo', 'website', 'contact_email', 'is_verified',
            'admin', 'admin_name', 'submission_count', 'created_at',
        ]
        read_only_fields = ['id', 'is_verified', 'admin', 'created_at']

    def get_admin_name(self, obj):
        return obj.admin.get_full_name() or obj.admin.username

    def get_submission_count(self, obj):
        return obj.submissions.count()

    def create(self, validated_data):
        if not validated_data.get('slug'):
            validated_data['slug'] = slugify(validated_data['name'])
        request = self.context['request']
        return Organization.objects.create(admin=request.user, **validated_data)


class StakeholderSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Stakeholder
        fields = ['id', 'organization', 'user', 'user_name', 'role', 'receives_all']

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
