from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.organizations.models import Organization
from apps.organizations.permissions import HasOrgPrivilege, IsOrgAdminOfOrg

from .models import Category, InvalidStatusTransitionError, StatusUpdate, Submission
from .serializers import (
    CategorySerializer,
    StatusUpdateSerializer,
    SubmissionSerializer,
    TrackSubmissionSerializer,
)
from .services import organization_stats, resolve_or_create_category, transition_status

SUBMISSION_QS = (
    Submission.objects.select_related('organization', 'category', 'citizen', 'branch', 'ai_insight', 'ai_suggestion')
    .prefetch_related('updates__updated_by')
)


def _resolve_org_for_request(request):
    """The org the current user acts within on the /org/* convenience
    endpoints: the org they administer, or (falling back) the org they hold
    an active staff membership in. None if neither applies.

    Without the staff fallback, OrgAdminSubmissionsView/OrgAdminStatsView
    would silently return nothing for every staff member — they were
    filtered on `organization__admin=request.user`, which is only ever true
    for the org_admin themselves.
    """
    org = Organization.objects.filter(admin=request.user).first()
    if org is not None:
        return org
    from apps.organizations.models import OrganizationStaff
    staff = (
        OrganizationStaff.objects.filter(user=request.user, status='active', is_active=True)
        .select_related('organization')
        .first()
    )
    return staff.organization if staff else None


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
        HasOrgPrivilege('manage_submissions').check(request, submission.organization)

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


class SubmissionVisibilityView(APIView):
    """PATCH /submissions/{reference}/visibility/ — toggle whether this
    submission appears on the organization's public showcase profile.
    Requires org admin or the 'manage_submissions' privilege (the same gate
    as status updates — showcasing is treated as part of normal case
    handling, not a separate concern)."""

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, reference_number):
        submission = get_object_or_404(SUBMISSION_QS, reference_number=reference_number)
        HasOrgPrivilege('manage_submissions').check(request, submission.organization)

        is_public = request.data.get('is_public')
        if not isinstance(is_public, bool):
            raise ValidationError({'is_public': 'This field is required and must be a boolean.'})

        submission.is_public = is_public
        submission.save(update_fields=['is_public', 'updated_at'])
        return Response(SubmissionSerializer(submission, context={'request': request}).data)


class SubmissionCategoryUpdateView(APIView):
    """PATCH /submissions/{reference}/category/ — manual categorization by
    staff. Requires the 'manage_submissions' privilege — same gate as status
    updates, since categorizing is part of ordinary case handling."""

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, reference_number):
        submission = get_object_or_404(SUBMISSION_QS, reference_number=reference_number)
        HasOrgPrivilege('manage_submissions').check(request, submission.organization)

        name = (request.data.get('category') or '').strip()
        if not name:
            raise ValidationError({'category': 'This field is required.'})

        submission.category = resolve_or_create_category(submission.organization, name)
        submission.save(update_fields=['category', 'updated_at'])
        return Response(SubmissionSerializer(submission, context={'request': request}).data)


class SubmissionAIClassifyView(APIView):
    """POST /submissions/{reference}/ai-classify/ — run AI classification for
    this submission (apps.ai_insights). Requires 'manage_submissions'.

    Returns 503 if AI features aren't configured for this deployment, 502 if
    the AI request itself fails — both distinct from a 500 so the frontend can
    show "AI unavailable" rather than a generic error.
    """

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'ai-classify'

    def post(self, request, reference_number):
        submission = get_object_or_404(SUBMISSION_QS, reference_number=reference_number)
        HasOrgPrivilege('manage_submissions').check(request, submission.organization)

        from apps.ai_insights.client import AIError
        from apps.ai_insights.services import classify_and_store, is_ai_enabled

        if not is_ai_enabled():
            return Response(
                {'detail': 'AI features are not configured for this deployment.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        try:
            _insight, applied = classify_and_store(submission)
        except AIError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        submission.refresh_from_db()
        return Response({
            'submission': SubmissionSerializer(submission, context={'request': request}).data,
            'applied': applied,
        })


class SubmissionAISuggestionView(APIView):
    """POST /submissions/{reference}/ai-suggestion/ — generate (or regenerate)
    the AI सुझाव for this submission. Requires 'manage_submissions'.

    Same 503/502 contract as SubmissionAIClassifyView.
    """

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'ai-suggestion'

    def post(self, request, reference_number):
        submission = get_object_or_404(SUBMISSION_QS, reference_number=reference_number)
        HasOrgPrivilege('manage_submissions').check(request, submission.organization)

        from apps.ai_insights.client import AIError
        from apps.ai_insights.services import generate_and_store_sujhav, is_ai_enabled

        if not is_ai_enabled():
            return Response(
                {'detail': 'AI features are not configured for this deployment.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        try:
            generate_and_store_sujhav(submission)
        except AIError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        submission.refresh_from_db()
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
    """GET /org/submissions/ — submissions for the org the current user
    administers or holds an active staff membership in (whichever applies —
    see _resolve_org_for_request). Requires the 'view_submissions' privilege
    for staff; org admins always pass.

    ?assigned_to=me scopes to the requesting staff member's own queue — the
    "assigned to me" widget on the staff dashboard.
    """

    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'priority', 'submission_type', 'branch']
    search_fields = ['title', 'reference_number']

    def get_queryset(self):
        org = _resolve_org_for_request(self.request)
        if org is None:
            return SUBMISSION_QS.none()
        HasOrgPrivilege('view_submissions').check(self.request, org)
        qs = SUBMISSION_QS.filter(organization=org)
        if self.request.query_params.get('assigned_to') == 'me':
            qs = qs.filter(assigned_to__user=self.request.user, assigned_to__organization=org)
        return qs


class OrgAIReportsView(generics.ListCreateAPIView):
    """GET /org/ai-reports/ — past AI reports for the current user's org.
    POST /org/ai-reports/ — generate a new one for {date_from, date_to}.

    Requires 'view_stats' (same gate as OrganizationStatsView — reports are a
    reporting feature, not case management).
    """

    pagination_class = None
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'ai-report'

    def get_serializer_class(self):
        from apps.ai_insights.serializers import AIReportSerializer
        return AIReportSerializer

    def _get_org(self):
        org = _resolve_org_for_request(self.request)
        if org is None:
            raise NotFound('You do not manage any organization.')
        HasOrgPrivilege('view_stats').check(self.request, org)
        return org

    def get_queryset(self):
        from apps.ai_insights.models import AIReport
        return AIReport.objects.filter(organization=self._get_org()).select_related('created_by')

    def create(self, request, *args, **kwargs):
        from apps.ai_insights.client import AIError
        from apps.ai_insights.services import generate_and_store_report, is_ai_enabled

        org = self._get_org()

        from django.utils.dateparse import parse_date

        date_from = parse_date(str(request.data.get('date_from') or ''))
        date_to = parse_date(str(request.data.get('date_to') or ''))
        if not date_from or not date_to:
            raise ValidationError({'date_from': 'Both date_from and date_to are required, as YYYY-MM-DD.'})
        if date_from > date_to:
            raise ValidationError({'date_from': 'date_from must not be after date_to.'})

        if not is_ai_enabled():
            return Response(
                {'detail': 'AI features are not configured for this deployment.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        try:
            report = generate_and_store_report(org, date_from, date_to, created_by=request.user)
        except AIError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        serializer = self.get_serializer(report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class OrgAdminStatsView(APIView):
    """GET /org/stats/ — dashboard stats for the org the current user
    administers or holds an active staff membership in."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        org = _resolve_org_for_request(request)
        if org is None:
            raise NotFound('You do not manage any organization.')
        HasOrgPrivilege('view_stats').check(request, org)
        return Response(organization_stats(org))


# How many recent branch-linked submissions feed the map's "thinking bubble"
# cycle — small on purpose, this is a live/glanceable view, not a report.
MAP_FEED_RECENT_LIMIT = 30
MAP_FEED_EXCERPT_LENGTH = 90


class OrgMapFeedView(APIView):
    """GET /org/map-feed/ — branches with coordinates + a rolling window of
    recent branch-linked submission excerpts, for the animated branch map
    (Branch pins + "thinking bubble" popups). Requires 'view_submissions' —
    it surfaces submission content (excerpts), not just aggregate counts.

    Excerpts never include submitter identity, matching the anonymity rule —
    only type/status/title feed the bubble text.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.organizations.models import Branch

        org = _resolve_org_for_request(request)
        if org is None:
            raise NotFound('You do not manage any organization.')
        HasOrgPrivilege('view_submissions').check(request, org)

        branches = Branch.objects.filter(
            organization=org, is_active=True,
            latitude__isnull=False, longitude__isnull=False,
        ).annotate(submission_count_annotated=Count('submissions', distinct=True))

        recent = (
            Submission.objects.filter(organization=org, branch__in=branches)
            .select_related('branch')
            .order_by('-created_at')[:MAP_FEED_RECENT_LIMIT]
        )

        return Response({
            'branches': [
                {
                    'id': b.id,
                    'name': b.name,
                    'latitude': float(b.latitude),
                    'longitude': float(b.longitude),
                    'submission_count': b.submission_count_annotated,
                }
                for b in branches
            ],
            'recent': [
                {
                    'branch_id': s.branch_id,
                    'reference_number': s.reference_number,
                    'excerpt': (
                        s.title if len(s.title) <= MAP_FEED_EXCERPT_LENGTH
                        else s.title[:MAP_FEED_EXCERPT_LENGTH].rsplit(' ', 1)[0] + '…'
                    ),
                    'type': s.submission_type,
                    'status': s.status,
                    'created_at': s.created_at,
                }
                for s in recent
            ],
        })


class SubmissionAssignView(APIView):
    """PATCH /submissions/{reference}/assign/ — assign to a staff member (org admin or 'assign_submissions')."""

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, reference_number):
        from apps.organizations.models import OrganizationStaff

        submission = get_object_or_404(SUBMISSION_QS, reference_number=reference_number)
        org = submission.organization

        HasOrgPrivilege('assign_submissions').check(request, org)

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
