from rest_framework import serializers

from .models import AIReport


class AIReportSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = AIReport
        fields = [
            'id', 'organization', 'date_from', 'date_to', 'submission_count',
            'summary_nepali', 'summary_english', 'themes', 'sentiment_overview',
            'recommendations', 'created_by_name', 'created_at',
        ]
        read_only_fields = fields

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None
