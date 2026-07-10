import base64
import io
from urllib.parse import urlparse

from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, F, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Organization, OrganizationStaff
from .permissions import IsOrgAdminOfOrg
from .serializers import OrganizationSerializer, OrganizationStaffSerializer

User = get_user_model()


def org_queryset_with_counts():
    return Organization.objects.annotate(
        submission_count_annotated=Count('submissions', distinct=True),
        resolved_count_annotated=Count(
            'submissions',
            filter=Q(submissions__status__in=['resolved', 'closed']),
            distinct=True,
        ),
        avg_resolution_annotated=Avg(
            F('submissions__resolved_at') - F('submissions__created_at'),
            filter=Q(submissions__resolved_at__isnull=False),
        ),
    ).order_by('name')


class OrganizationListCreateView(generics.ListCreateAPIView):
    """
    GET  /organizations/ — public list of active, verified organizations.
    POST /organizations/ — register a new organization (authenticated users).
    """

    serializer_class = OrganizationSerializer
    search_fields = ['name', 'category', 'description']
    filterset_fields = ['category']

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = org_queryset_with_counts().filter(is_active=True)
        user = self.request.user
        if user.is_authenticated:
            return qs.filter(Q(is_verified=True) | Q(admin=user))
        return qs.filter(is_verified=True)


class OrganizationDetailView(generics.RetrieveAPIView):
    """GET /organizations/{slug}/ — public organization profile."""

    serializer_class = OrganizationSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'

    def get_queryset(self):
        return org_queryset_with_counts().filter(is_active=True)


class MyOrganizationView(APIView):
    """GET /organizations/mine/ — the organization managed by the current user."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        org = org_queryset_with_counts().filter(admin=request.user).first()
        if org is None:
            return Response({'detail': 'You do not manage any organization.'}, status=404)
        return Response(OrganizationSerializer(org).data)


class OrganizationSubmissionsView(generics.ListAPIView):
    """GET /organizations/{slug}/submissions/ — org admin only."""

    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'priority', 'submission_type']

    def get_serializer_class(self):
        from apps.submissions.serializers import SubmissionSerializer
        return SubmissionSerializer

    def get_queryset(self):
        from apps.submissions.models import Submission
        org = get_object_or_404(Organization, slug=self.kwargs['slug'])
        IsOrgAdminOfOrg().check(self.request, org)
        return (
            Submission.objects.filter(organization=org)
            .select_related('organization', 'category', 'citizen')
            .prefetch_related('updates__updated_by')
        )


class OrganizationStatsView(APIView):
    """GET /organizations/{slug}/stats/ — aggregate counts, org admin only."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, slug):
        from apps.submissions.services import organization_stats
        org = get_object_or_404(Organization, slug=slug)
        IsOrgAdminOfOrg().check(request, org)
        return Response(organization_stats(org))


class OrganizationStaffView(generics.ListAPIView):
    """GET /organizations/{slug}/staff/ — list staff; POST — add staff member."""

    serializer_class = OrganizationStaffSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def _get_org(self):
        org = get_object_or_404(Organization, slug=self.kwargs['slug'])
        IsOrgAdminOfOrg().check(self.request, org)
        return org

    def get_queryset(self):
        return (
            OrganizationStaff.objects.filter(organization=self._get_org())
            .select_related('user', 'assigned_by')
        )

    def post(self, request, slug):
        org = self._get_org()
        user_email = (request.data.get('user_email') or '').strip().lower()
        role = request.data.get('role', 'agent')

        if not user_email:
            raise ValidationError({'user_email': 'This field is required.'})

        valid_roles = {r for r, _ in OrganizationStaff.ROLE_CHOICES}
        if role not in valid_roles:
            raise ValidationError({'role': f'Must be one of: {sorted(valid_roles)}'})

        try:
            user = User.objects.get(email__iexact=user_email)
        except User.DoesNotExist:
            raise ValidationError({'user_email': f'No registered user found with email "{user_email}".'})

        if OrganizationStaff.objects.filter(organization=org, user=user).exists():
            raise ValidationError({'user_email': 'This user is already a staff member of this organization.'})

        staff = OrganizationStaff.objects.create(
            organization=org,
            user=user,
            role=role,
            assigned_by=request.user,
        )
        return Response(OrganizationStaffSerializer(staff).data, status=status.HTTP_201_CREATED)


class OrganizationStaffDetailView(APIView):
    """PATCH/DELETE /organizations/{slug}/staff/{staff_id}/ — update role or remove staff."""

    permission_classes = [permissions.IsAuthenticated]

    def _get_objects(self, request, slug, staff_id):
        org = get_object_or_404(Organization, slug=slug)
        IsOrgAdminOfOrg().check(request, org)
        staff = get_object_or_404(OrganizationStaff, pk=staff_id, organization=org)
        return org, staff

    def patch(self, request, slug, staff_id):
        _, staff = self._get_objects(request, slug, staff_id)
        serializer = OrganizationStaffSerializer(staff, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, slug, staff_id):
        _, staff = self._get_objects(request, slug, staff_id)
        staff.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrganizationQRCodeView(APIView):
    """GET /organizations/{slug}/qrcode/ — PNG QR or base64 JSON linking to the submission page."""

    permission_classes = [permissions.AllowAny]

    def perform_content_negotiation(self, request, force=False):
        # Skip DRF format interception — this view returns raw Django responses and
        # reads ?format= itself, so we must prevent DRF from raising Http404 on
        # unknown format values like 'base64'.
        renderers = self.get_renderers()
        if renderers:
            return renderers[0], renderers[0].media_type
        return None, None

    @staticmethod
    def _resolve_frontend_url(request) -> str:
        """The origin the visitor is browsing on (?origin=), else FRONTEND_URL.

        The QR code only encodes a link back to this platform's submit page, so
        honouring the caller-provided origin keeps QR codes scannable when the
        app is served through a tunnel or an alternate domain.
        """
        origin = request.query_params.get('origin', '')
        parsed = urlparse(origin)
        if parsed.scheme in ('http', 'https') and parsed.netloc:
            return f'{parsed.scheme}://{parsed.netloc}'
        return getattr(django_settings, 'FRONTEND_URL', 'http://localhost:3000')

    def get(self, request, slug):
        import qrcode

        org = get_object_or_404(Organization, slug=slug, is_active=True)
        frontend_url = self._resolve_frontend_url(request)
        target_url = f'{frontend_url}/submit/{slug}'

        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(target_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        # Use raw Django responses (not DRF Response) to avoid DRF intercepting
        # ?format= as a renderer format suffix and returning 404.
        fmt = request.query_params.get('format', 'png').lower()
        if fmt == 'base64':
            b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return JsonResponse({
                'qr_code': f'data:image/png;base64,{b64}',
                'url': target_url,
                'org_name': org.name,
                'org_slug': slug,
            })

        return HttpResponse(buffer.getvalue(), content_type='image/png')
