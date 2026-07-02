from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import Category, Submission, StatusUpdate
from .serializers import CategorySerializer, SubmissionSerializer, StatusUpdateSerializer


class CategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Category.objects.select_related('organization').all()
        org_id = self.request.query_params.get('org')
        org_slug = self.request.query_params.get('org_slug')
        if org_id:
            queryset = queryset.filter(organization_id=org_id)
        elif org_slug:
            queryset = queryset.filter(organization__slug=org_slug)
        return queryset


class SubmissionListCreateView(generics.ListCreateAPIView):
    serializer_class = SubmissionSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'org_admin':
            from apps.organizations.models import Organization
            orgs = Organization.objects.filter(admin=user)
            return Submission.objects.filter(organization__in=orgs)
        return Submission.objects.filter(citizen=user)


class SubmissionDetailView(generics.RetrieveAPIView):
    serializer_class = SubmissionSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'reference_number'
    queryset = Submission.objects.all()


class SubmissionStatusUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, reference_number):
        submission = get_object_or_404(Submission, reference_number=reference_number)

        if request.user != submission.organization.admin and not request.user.is_staff:
            return Response(
                {'detail': 'Only this organization\'s admin can update submission status.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        new_status = request.data.get('status')
        if not new_status:
            return Response({'detail': 'status field is required.'}, status=status.HTTP_400_BAD_REQUEST)

        valid_statuses = [s for s, _ in Submission.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response(
                {'detail': f'Invalid status. Valid choices: {valid_statuses}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = submission.status
        submission.status = new_status
        submission.save(update_fields=['status', 'updated_at'])

        StatusUpdate.objects.create(
            submission=submission,
            updated_by=request.user,
            old_status=old_status,
            new_status=new_status,
            note=request.data.get('note', ''),
        )

        serializer = SubmissionSerializer(submission, context={'request': request})
        return Response(serializer.data)


class SubmissionUpdatesView(generics.ListCreateAPIView):
    serializer_class = StatusUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _get_submission(self):
        return get_object_or_404(Submission, reference_number=self.kwargs['reference_number'])

    def get_queryset(self):
        submission = self._get_submission()
        return StatusUpdate.objects.filter(submission=submission)

    def perform_create(self, serializer):
        submission = self._get_submission()
        if self.request.user != submission.organization.admin and not self.request.user.is_staff:
            raise PermissionDenied('Only this organization\'s admin can add status notes.')
        serializer.save(
            submission=submission,
            updated_by=self.request.user,
            old_status=submission.status,
            new_status=submission.status,
        )
