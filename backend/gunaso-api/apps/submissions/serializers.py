from django.utils import timezone
from rest_framework import serializers
from .models import Category, Submission, StatusUpdate


class CategorySerializer(serializers.ModelSerializer):
    organization_name = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'organization', 'organization_name']

    def get_organization_name(self, obj):
        return obj.organization.name if obj.organization else 'Global'


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

    def get_updated_by_name(self, obj):
        if obj.updated_by:
            return obj.updated_by.get_full_name() or obj.updated_by.username
        return 'System'


class SubmissionSerializer(serializers.ModelSerializer):
    updates = StatusUpdateSerializer(many=True, read_only=True)
    citizen_display_name = serializers.SerializerMethodField()
    organization_name = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = [
            'id', 'reference_number',
            'citizen', 'citizen_display_name',
            'citizen_name', 'citizen_email', 'citizen_phone',
            'organization', 'organization_name',
            'category', 'category_name',
            'submission_type', 'title', 'description', 'attachment',
            'status', 'priority', 'is_anonymous',
            'created_at', 'updated_at', 'updates',
        ]
        read_only_fields = [
            'id', 'reference_number', 'citizen', 'status',
            'created_at', 'updated_at',
        ]

    def get_citizen_display_name(self, obj):
        if obj.is_anonymous:
            return 'Anonymous'
        return obj.citizen_name

    def get_organization_name(self, obj):
        return obj.organization.name if obj.organization else None

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_anonymous:
            data['citizen'] = None
            data['citizen_name'] = 'Anonymous'
            data['citizen_email'] = '***@***.***'
            data['citizen_phone'] = '***'
        return data

    def create(self, validated_data):
        request = self.context.get('request')

        year = timezone.now().year
        count = Submission.objects.count() + 1
        ref_number = f'GUN-{year}-{count:05d}'
        while Submission.objects.filter(reference_number=ref_number).exists():
            count += 1
            ref_number = f'GUN-{year}-{count:05d}'

        citizen = None
        if request and request.user.is_authenticated:
            citizen = request.user
            if not validated_data.get('citizen_name') and citizen.get_full_name():
                validated_data.setdefault('citizen_name', citizen.get_full_name())
            if not validated_data.get('citizen_email') and citizen.email:
                validated_data.setdefault('citizen_email', citizen.email)

        return Submission.objects.create(
            reference_number=ref_number,
            citizen=citizen,
            **validated_data,
        )
