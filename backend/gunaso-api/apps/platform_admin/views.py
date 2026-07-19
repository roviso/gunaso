from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.organizations.models import Organization, OrganizationStaff
from apps.organizations.serializers import OrganizationStaffSerializer
from apps.organizations.views import org_queryset_with_counts

from .permissions import IsSuperAdmin
from .models import PlatformAuditLog
from .serializers import AdminOrganizationSerializer, AdminUserSerializer, PlatformAuditLogSerializer
from .services import (
    block_user,
    demote_superadmin,
    platform_overview,
    promote_to_superadmin,
    set_organization_active,
    unblock_user,
    verify_organization,
)

User = get_user_model()


class AdminOverviewView(APIView):
    """GET /admin/overview/ — platform-wide analytics for the superadmin dashboard."""

    permission_classes = [IsSuperAdmin]

    def get(self, request):
        return Response(platform_overview())


class AdminOrganizationListView(generics.ListAPIView):
    """GET /admin/organizations/ — every organization, verified or not, active or not."""

    serializer_class = AdminOrganizationSerializer
    permission_classes = [IsSuperAdmin]
    search_fields = ['name', 'category', 'contact_email']
    filterset_fields = ['is_verified', 'is_active', 'category']

    def get_queryset(self):
        return org_queryset_with_counts().select_related('admin')


class AdminOrganizationActionView(APIView):
    """PATCH /admin/organizations/{slug}/ — verify/unverify and/or activate/deactivate.

    Body may include either or both of `is_verified`/`is_active`; each
    supplied key is applied through its own service call so the audit log
    records them as distinct, individually-reversible actions.
    """

    permission_classes = [IsSuperAdmin]

    def patch(self, request, slug):
        org = get_object_or_404(Organization, slug=slug)
        if 'is_verified' in request.data:
            org = verify_organization(org, request.user, bool(request.data['is_verified']))
        if 'is_active' in request.data:
            org = set_organization_active(org, request.user, bool(request.data['is_active']))
        return Response(AdminOrganizationSerializer(org).data)


class AdminOrganizationStaffView(generics.ListAPIView):
    """GET /admin/organizations/{slug}/staff/ — that organization's staff roster."""

    serializer_class = OrganizationStaffSerializer
    permission_classes = [IsSuperAdmin]
    pagination_class = None

    def get_queryset(self):
        org = get_object_or_404(Organization, slug=self.kwargs['slug'])
        return (
            OrganizationStaff.objects.filter(organization=org)
            .select_related('user', 'role', 'assigned_by')
        )


class AdminUserListView(generics.ListAPIView):
    """GET /admin/users/ — every platform user, any type or status."""

    serializer_class = AdminUserSerializer
    permission_classes = [IsSuperAdmin]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    filterset_fields = ['user_type', 'is_active', 'is_staff', 'is_superuser']

    def get_queryset(self):
        return User.objects.all().order_by('-date_joined')


class AdminUserBlockView(APIView):
    """POST /admin/users/{id}/block/ — deactivate the account and revoke its sessions."""

    permission_classes = [IsSuperAdmin]

    def post(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        user = block_user(user, request.user)
        return Response(AdminUserSerializer(user).data)


class AdminUserUnblockView(APIView):
    """POST /admin/users/{id}/unblock/"""

    permission_classes = [IsSuperAdmin]

    def post(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        user = unblock_user(user, request.user)
        return Response(AdminUserSerializer(user).data)


class AdminUserPromoteView(APIView):
    """POST /admin/users/{id}/promote/ — grant superadmin (is_staff + is_superuser)."""

    permission_classes = [IsSuperAdmin]

    def post(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        user = promote_to_superadmin(user, request.user)
        return Response(AdminUserSerializer(user).data)


class AdminUserDemoteView(APIView):
    """POST /admin/users/{id}/demote/ — revoke superadmin."""

    permission_classes = [IsSuperAdmin]

    def post(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        user = demote_superadmin(user, request.user)
        return Response(AdminUserSerializer(user).data)


class AdminSubmissionListView(generics.ListAPIView):
    """GET /admin/submissions/ — cross-organization submission feed.

    Reuses SubmissionSerializer, whose anonymity/contact redaction already
    special-cases `user.is_staff` (see apps/submissions/serializers.py) — a
    superadmin (always is_staff=True, see services.promote_to_superadmin)
    sees full submitter identity, including anonymous submitters, same as
    any other platform staff account.
    """

    permission_classes = [IsSuperAdmin]
    filterset_fields = ['status', 'priority', 'submission_type', 'organization']
    search_fields = ['title', 'reference_number', 'citizen_name']

    def get_serializer_class(self):
        from apps.submissions.serializers import SubmissionSerializer
        return SubmissionSerializer

    def get_queryset(self):
        from apps.submissions.models import Submission
        return (
            Submission.objects.all()
            .select_related('organization', 'category', 'citizen', 'branch', 'ai_insight', 'ai_suggestion')
            .prefetch_related('updates__updated_by')
        )


class AdminAuditLogListView(generics.ListAPIView):
    """GET /admin/audit-log/ — append-only record of every superadmin action."""

    serializer_class = PlatformAuditLogSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        return PlatformAuditLog.objects.select_related('actor')
