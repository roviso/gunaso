from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.organizations.models import Organization
from apps.organizations.permissions import IsOrgAdminOfOrg

from .models import Category, InvalidStatusTransitionError, StatusUpdate, Submission
from .serializers import (
    CategorySerializer,
    StatusUpdateSerializer,
    SubmissionSerializer,
    TrackSubmissionSerializer,
)
from .services import organization_stats, transition_status

SUBMISSION_QS = (
    Submission.objects.select_related('organization', 'category', 'citizen')
    .prefetch_related('updates__updated_by')
)


class CategoryListView(generics.ListAPIView):
    """GET /categories/?org=<id>|org_slug=<slug> — public category taxonomy."""

    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        queryset = Category.objects.select_related('organization').filter(is_active=True)
        org_id = self.request.query_params.get('org')
        org_slug = self.request.query_params.get('org_slug')
        if org_id:
            queryset = queryset.filter(organization_id=org_id)
        elif org_slug:
            queryset = queryset.filter(organization__slug=org_slug)
        return queryset


class SubmissionCreateView(generics.CreateAPIView):
    """POST /submissions/ — anyone (including anonymous citizens) may submit."""

    serializer_class = SubmissionSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'submission-create'


class MySubmissionsView(generics.ListAPIView):
    """GET /submissions/my/ — the authenticated citizen's own submissions."""

    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'priority', 'submission_type']

    def get_queryset(self):
        return SUBMISSION_QS.filter(citizen=self.request.user)


class TrackSubmissionView(generics.RetrieveAPIView):
    """GET /submissions/track/{reference}/ — public tracking with redacted identity."""

    serializer_class = TrackSubmissionSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'reference_number'
    lookup_url_kwarg = 'reference_number'
    queryset = SUBMISSION_QS

    def get_object(self):
        ref = self.kwargs['reference_number'].upper().strip()
        try:
            return self.get_queryset().get(reference_number=ref)
        except Submission.DoesNotExist:
            raise NotFound('No submission found with that reference number.')


class SubmissionDetailView(generics.RetrieveAPIView):
    """GET /submissions/{reference}/ — owner, org admin, or platform staff only."""

    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'reference_number'
    queryset = SUBMISSION_QS

    def get_object(self):
        submission = super().get_object()
        user = self.request.user
        if not (
            user.is_staff
            or submission.citizen_id == user.id
            or submission.organization.admin_id == user.id
        ):
            raise PermissionDenied('You do not have access to this submission.')
        return submission


class SubmissionStatusUpdateView(APIView):
    """PATCH /submissions/{reference}/status/ — validated transitions, org admin only."""

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, reference_number):
        submission = get_object_or_404(SUBMISSION_QS, reference_number=reference_number)
        IsOrgAdminOfOrg().check(request, submission.organization)

        new_status = request.data.get('status')
        if not new_status:
            raise ValidationError({'status': 'This field is required.'})
        valid_statuses = {s for s, _ in Submission.STATUS_CHOICES}
        if new_status not in valid_statuses:
            raise ValidationError({'status': f'Invalid status. Valid choices: {sorted(valid_statuses)}'})

        try:
            transition_status(
                submission, new_status,
                changed_by=request.user,
                note=str(request.data.get('note', ''))[:2000],
            )
        except InvalidStatusTransitionError as exc:
            return Response(
                {'detail': str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        # Re-fetch so the serialized timeline includes the update we just appended.
        submission = SUBMISSION_QS.get(pk=submission.pk)
        return Response(SubmissionSerializer(submission, context={'request': request}).data)


class SubmissionUpdatesView(generics.ListCreateAPIView):
    """GET/POST /submissions/{reference}/updates/ — audit trail and staff notes."""

    serializer_class = StatusUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def _get_submission(self):
        return get_object_or_404(SUBMISSION_QS, reference_number=self.kwargs['reference_number'])

    def get_queryset(self):
        submission = self._get_submission()
        user = self.request.user
        if not (
            user.is_staff
            or submission.citizen_id == user.id
            or submission.organization.admin_id == user.id
        ):
            raise PermissionDenied('You do not have access to this submission.')
        return StatusUpdate.objects.filter(submission=submission).select_related('updated_by')

    def perform_create(self, serializer):
        submission = self._get_submission()
        IsOrgAdminOfOrg().check(self.request, submission.organization)
        serializer.save(
            submission=submission,
            updated_by=self.request.user,
            old_status=submission.status,
            new_status=submission.status,
        )


class OrgAdminSubmissionsView(generics.ListAPIView):
    """GET /org/submissions/ — all submissions across orgs managed by the current user."""

    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'priority', 'submission_type']
    search_fields = ['title', 'reference_number']

    def get_queryset(self):
        return SUBMISSION_QS.filter(organization__admin=self.request.user)


class OrgAdminStatsView(APIView):
    """GET /org/stats/ — dashboard stats for the org managed by the current user."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        org = Organization.objects.filter(admin=request.user).first()
        if org is None:
            raise NotFound('You do not manage any organization.')
        return Response(organization_stats(org))


class SubmissionAssignView(APIView):
    """PATCH /submissions/{reference}/assign/ — assign to a staff member (org admin or supervisor)."""

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, reference_number):
        from apps.organizations.models import OrganizationStaff

        submission = get_object_or_404(SUBMISSION_QS, reference_number=reference_number)
        user = request.user
        org = submission.organization

        is_org_admin = org.admin_id == user.id or user.is_staff
        is_supervisor = (
            not is_org_admin
            and OrganizationStaff.objects.filter(
                organization=org, user=user, role='supervisor', is_active=True
            ).exists()
        )

        if not (is_org_admin or is_supervisor):
            raise PermissionDenied('Only org admins or supervisors can assign submissions.')

        staff_id = request.data.get('staff_id')
        if staff_id is None:
            raise ValidationError({'staff_id': 'This field is required.'})

        try:
            staff_id = int(staff_id)
        except (TypeError, ValueError):
            raise ValidationError({'staff_id': 'Must be an integer.'})

        staff = get_object_or_404(
            OrganizationStaff,
            pk=staff_id,
            organization=org,
            is_active=True,
        )

        submission.assigned_to = staff
        submission.save(update_fields=['assigned_to', 'updated_at'])

        return Response(SubmissionSerializer(submission, context={'request': request}).data)
