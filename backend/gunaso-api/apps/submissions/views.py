import csv
from datetime import timedelta

from django.db.models import Count, OuterRef, Q, Subquery
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.organizations.models import Organization
from apps.organizations.permissions import HasOrgPrivilege

from .models import Category, InvalidStatusTransitionError, StatusUpdate, Submission
from .serializers import (
    CategorySerializer,
    CitizenReplySerializer,
    SatisfactionSerializer,
    StatusUpdateSerializer,
    SubmissionSerializer,
    TrackSubmissionSerializer,
)
from .services import (
    ACTIVE_STATUSES,
    FollowUpError,
    is_overdue,
    add_citizen_reply,
    add_staff_note,
    has_followup_access,
    organization_stats,
    overdue_q,
    public_platform_stats,
    record_satisfaction,
    resolve_or_create_category,
    transition_status,
)

SUBMISSION_QS = (
    Submission.objects.select_related('organization', 'category', 'citizen', 'branch', 'ai_insight', 'ai_suggestion')
    .prefetch_related('updates__updated_by')
)


def _can_view_submission(request, submission) -> bool:
    """Owner, platform staff, the org admin, or org staff with 'view_submissions'."""
    user = request.user
    return (
        submission.citizen_id == user.id
        or HasOrgPrivilege('view_submissions').has_object_permission(request, None, submission.organization)
    )


def _last_public_update_kind():
    """Subquery: the kind of the most recent citizen-visible timeline entry —
    'citizen_reply' means the citizen is waiting on the organization."""
    return Subquery(
        StatusUpdate.objects.filter(submission=OuterRef('pk'))
        .exclude(kind=StatusUpdate.KIND_INTERNAL_NOTE)
        .order_by('-created_at', '-id')
        .values('kind')[:1]
    )


def _apply_queue_filters(request, qs, org):
    """Filters shared by the org submissions list and its CSV export:
    ?assigned_to=me, ?overdue=true, ?awaiting_reply=true."""
    params = request.query_params
    if params.get('assigned_to') == 'me':
        qs = qs.filter(assigned_to__user=request.user, assigned_to__organization=org)
    elif params.get('assigned_to') == 'none':
        qs = qs.filter(assigned_to__isnull=True)
    if params.get('overdue') in ('1', 'true'):
        qs = qs.filter(overdue_q())
    if params.get('awaiting_reply') in ('1', 'true'):
        qs = qs.annotate(last_public_kind=_last_public_update_kind()).filter(
            last_public_kind=StatusUpdate.KIND_CITIZEN_REPLY,
        )
    if params.get('open') in ('1', 'true'):
        qs = qs.filter(status__in=ACTIVE_STATUSES)
    return qs


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

    def get_serializer_context(self):
        # The private key travels in a header (read from the URL fragment by
        # the SPA), never the query string — so it stays out of access logs.
        context = super().get_serializer_context()
        if 'reference_number' in self.kwargs:
            context['followup_access'] = has_followup_access(
                self.get_object(), self.request.user,
                self.request.headers.get('X-Followup-Key', ''),
            )
        return context


class _FollowUpView(APIView):
    """Base for the submitter's own follow-up actions on the public track
    page. Allowed for the signed-in owner or anyone holding the private
    follow-up key; everyone else gets the same 403 whether or not the
    reference exists, so this can't be used to probe for valid keys."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'followup'
    serializer_class = None

    def _authorize(self, request, reference_number):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        ref = reference_number.upper().strip()
        submission = SUBMISSION_QS.filter(reference_number=ref).first()
        key = serializer.validated_data.get('key', '')
        if submission is None or not has_followup_access(submission, request.user, key):
            raise PermissionDenied('This follow-up link is invalid. Use the private link from your confirmation.')
        return submission, serializer.validated_data

    def _respond(self, request, submission, status_code=status.HTTP_200_OK):
        submission = SUBMISSION_QS.get(pk=submission.pk)
        serializer = TrackSubmissionSerializer(
            submission, context={'request': request, 'followup_access': True},
        )
        return Response(serializer.data, status=status_code)


class SubmissionCitizenReplyView(_FollowUpView):
    """POST /submissions/track/{reference}/reply/ — the submitter adds a
    follow-up message to their own case ({message, key?})."""

    serializer_class = CitizenReplySerializer

    def post(self, request, reference_number):
        submission, data = self._authorize(request, reference_number)
        try:
            add_citizen_reply(submission, data['message'].strip(), user=request.user)
        except FollowUpError as exc:
            return Response({'detail': exc.message}, status=status.HTTP_409_CONFLICT)
        return self._respond(request, submission, status.HTTP_201_CREATED)


class SubmissionSatisfactionView(_FollowUpView):
    """POST /submissions/track/{reference}/feedback/ — the submitter rates
    how their case was handled ({score 1–5, comment?, key?}). Only once it's
    resolved/rejected/closed; re-rating overwrites."""

    serializer_class = SatisfactionSerializer

    def post(self, request, reference_number):
        submission, data = self._authorize(request, reference_number)
        try:
            record_satisfaction(submission, data['score'], data.get('comment', '').strip())
        except FollowUpError as exc:
            return Response({'detail': exc.message}, status=status.HTTP_409_CONFLICT)
        return self._respond(request, submission)


class SubmissionDetailView(generics.RetrieveAPIView):
    """GET /submissions/{reference}/ — owner, org admin, org staff with
    'view_submissions', or platform staff."""

    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'reference_number'
    queryset = SUBMISSION_QS

    def get_object(self):
        submission = super().get_object()
        if not _can_view_submission(self.request, submission):
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
    """GET/POST /submissions/{reference}/updates/ — audit trail and staff notes.

    GET: the owner, or anyone who can view the org's submissions. Internal
    notes are only listed for the organization side.
    POST: 'manage_submissions' — a public reply (emailed to the citizen) or,
    with `internal: true`, an organization-only note.
    """

    serializer_class = StatusUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def _get_submission(self):
        return get_object_or_404(SUBMISSION_QS, reference_number=self.kwargs['reference_number'])

    def get_queryset(self):
        submission = self._get_submission()
        if not _can_view_submission(self.request, submission):
            raise PermissionDenied('You do not have access to this submission.')
        qs = StatusUpdate.objects.filter(submission=submission).select_related('updated_by', 'submission')
        is_insider = HasOrgPrivilege('view_submissions').has_object_permission(
            self.request, None, submission.organization,
        )
        if not is_insider:
            qs = qs.exclude(kind=StatusUpdate.KIND_INTERNAL_NOTE)
        return qs

    def create(self, request, *args, **kwargs):
        submission = self._get_submission()
        HasOrgPrivilege('manage_submissions').check(request, submission.organization)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        update = add_staff_note(
            submission,
            serializer.validated_data['note'].strip(),
            author=request.user,
            internal=serializer.validated_data.get('internal', False),
        )
        return Response(self.get_serializer(update).data, status=status.HTTP_201_CREATED)


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
    search_fields = ['title', 'reference_number', 'description']
    ordering_fields = ['created_at', 'updated_at', 'priority', 'status']

    def get_queryset(self):
        org = _resolve_org_for_request(self.request)
        if org is None:
            return SUBMISSION_QS.none()
        HasOrgPrivilege('view_submissions').check(self.request, org)
        return _apply_queue_filters(self.request, SUBMISSION_QS.filter(organization=org), org)


# Hard cap on one export — a spreadsheet, not a data-dump endpoint.
EXPORT_MAX_ROWS = 10000


def _csv_safe(value) -> str:
    """Neutralize spreadsheet formula injection: a citizen-typed title like
    '=HYPERLINK(...)' must not execute when staff open the export in Excel."""
    text = '' if value is None else str(value)
    if text and text[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + text
    return text


class OrgSubmissionsExportView(generics.GenericAPIView):
    """GET /org/submissions/export/ — the org's submissions as CSV, with the
    same filters as /org/submissions/. Requires 'view_submissions'.

    Contact columns follow the serializer's rules exactly: anonymous
    submitters are never identified, and contact details are only filled in
    for viewers who may see them ('manage_submissions').
    """

    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'priority', 'submission_type', 'branch']
    search_fields = ['title', 'reference_number', 'description']

    def get_queryset(self):
        org = _resolve_org_for_request(self.request)
        if org is None:
            raise NotFound('You do not manage any organization.')
        HasOrgPrivilege('view_submissions').check(self.request, org)
        self._org = org
        qs = Submission.objects.filter(organization=org).select_related(
            'category', 'branch', 'assigned_to__user', 'organization',
        )
        return _apply_queue_filters(self.request, qs, org)

    def get(self, request):
        from apps.organizations.permissions import org_privileges_for

        qs = self.filter_queryset(self.get_queryset()).order_by('-created_at')[:EXPORT_MAX_ROWS]
        can_contact = 'manage_submissions' in org_privileges_for(request.user, self._org)

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        stamp = timezone.now().strftime('%Y%m%d-%H%M')
        response['Content-Disposition'] = f'attachment; filename="{self._org.slug}-gunaso-{stamp}.csv"'
        response.write('\ufeff')  # BOM so Excel opens Devanagari text as UTF-8
        writer = csv.writer(response)
        writer.writerow([
            'Reference', 'Submitted at', 'Type', 'Category', 'Title', 'Description',
            'Status', 'Priority', 'Branch', 'Assigned to', 'Submitter', 'Email', 'Phone',
            'Resolved at', 'Satisfaction (1-5)', 'Overdue',
        ])
        now = timezone.now()
        for s in qs:
            anonymous = s.is_anonymous
            writer.writerow([_csv_safe(v) for v in [
                s.reference_number,
                s.created_at.isoformat(timespec='minutes'),
                s.get_submission_type_display(),
                s.category.name if s.category_id else '',
                s.title,
                s.description,
                s.get_status_display(),
                s.get_priority_display(),
                s.branch.name if s.branch_id else '',
                (s.assigned_to.user.get_full_name() or s.assigned_to.user.username) if s.assigned_to_id else '',
                'Anonymous' if anonymous else s.citizen_name,
                '' if anonymous or not can_contact else s.citizen_email,
                '' if anonymous or not can_contact else s.citizen_phone,
                s.resolved_at.isoformat(timespec='minutes') if s.resolved_at else '',
                s.satisfaction_score or '',
                'yes' if is_overdue(s, now) else '',
            ]])
        return response


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


MAP_FEED_WINDOWS = {'7': 7, '30': 30, '90': 90}


class OrgMapFeedView(APIView):
    """GET /org/map-feed/?days=7|30|90 — branches with coordinates, per-branch
    workload (open / overdue / resolved / by type) and a rolling window of
    recent branch-linked submission excerpts, for the branch hotspot map.
    Requires 'view_submissions' — it surfaces submission content (excerpts),
    not just aggregate counts.

    `days` narrows every count and the excerpt feed to that window (omit it
    for all time). Excerpts never include submitter identity, matching the
    anonymity rule — only type/status/title feed the bubble text.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.organizations.models import Branch

        org = _resolve_org_for_request(request)
        if org is None:
            raise NotFound('You do not manage any organization.')
        HasOrgPrivilege('view_submissions').check(request, org)

        window = MAP_FEED_WINDOWS.get(request.query_params.get('days', ''))
        in_window = Q()
        if window:
            in_window = Q(submissions__created_at__gte=timezone.now() - timedelta(days=window))

        def counted(extra=Q()):
            return Count('submissions', filter=in_window & extra, distinct=True)

        branches = Branch.objects.filter(
            organization=org, is_active=True,
            latitude__isnull=False, longitude__isnull=False,
        ).annotate(
            submission_count_annotated=counted(),
            open_count=counted(Q(submissions__status__in=ACTIVE_STATUSES)),
            resolved_count=counted(Q(submissions__status__in=['resolved', 'closed'])),
            complaint_count=counted(Q(submissions__submission_type='complaint')),
            feedback_count=counted(Q(submissions__submission_type='feedback')),
            suggestion_count=counted(Q(submissions__submission_type='suggestion')),
        )

        recent_qs = Submission.objects.filter(organization=org, branch__in=branches)
        if window:
            recent_qs = recent_qs.filter(created_at__gte=timezone.now() - timedelta(days=window))
        overdue_by_branch = dict(
            recent_qs.filter(overdue_q()).values_list('branch_id').annotate(n=Count('id')).order_by()
        )
        unlinked = Submission.objects.filter(organization=org, branch__isnull=True)
        if window:
            unlinked = unlinked.filter(created_at__gte=timezone.now() - timedelta(days=window))
        recent = recent_qs.select_related('branch').order_by('-created_at')[:MAP_FEED_RECENT_LIMIT]

        return Response({
            'window_days': window,
            'unlinked_count': unlinked.count(),
            'branches': [
                {
                    'id': b.id,
                    'name': b.name,
                    'address': b.address,
                    'latitude': float(b.latitude),
                    'longitude': float(b.longitude),
                    'submission_count': b.submission_count_annotated,
                    'open_count': b.open_count,
                    'resolved_count': b.resolved_count,
                    'overdue_count': overdue_by_branch.get(b.id, 0),
                    'by_type': {
                        'complaint': b.complaint_count,
                        'feedback': b.feedback_count,
                        'suggestion': b.suggestion_count,
                    },
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

        if 'staff_id' not in request.data:
            raise ValidationError({'staff_id': 'This field is required.'})
        staff_id = request.data.get('staff_id')
        if staff_id in (None, ''):
            # Explicit null/blank unassigns.
            submission.assigned_to = None
            submission.save(update_fields=['assigned_to', 'updated_at'])
            submission = SUBMISSION_QS.get(pk=submission.pk)
            return Response(SubmissionSerializer(submission, context={'request': request}).data)

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
        submission = SUBMISSION_QS.get(pk=submission.pk)
        return Response(SubmissionSerializer(submission, context={'request': request}).data)


class PublicStatsView(APIView):
    """GET /public/stats/ — aggregate, identity-free platform numbers for the
    landing page (counts and rates only; verified organizations only)."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(public_platform_stats())


PUBLIC_STORIES_LIMIT = 6


class PublicStoriesView(generics.ListAPIView):
    """GET /public/stories/ — the most recent submissions organizations have
    chosen to showcase (Submission.is_public), across verified orgs. Same
    redaction as the org showcase: TrackSubmissionSerializer never exposes
    contact details, internal notes, or an anonymous submitter's name."""

    permission_classes = [permissions.AllowAny]
    serializer_class = TrackSubmissionSerializer
    pagination_class = None

    def get_queryset(self):
        return SUBMISSION_QS.filter(
            is_public=True,
            organization__is_active=True,
            organization__is_verified=True,
        ).order_by('-updated_at')[:PUBLIC_STORIES_LIMIT]
