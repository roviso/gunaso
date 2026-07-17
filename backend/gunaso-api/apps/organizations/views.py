import base64
import io
from urllib.parse import urlparse

from django.conf import settings as django_settings
from django.db.models import Avg, Count, F, IntegerField, OuterRef, ProtectedError, Q, Subquery
from django.db.models.functions import Coalesce
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.views import _auth_payload, _set_refresh_cookie

from .models import Organization, OrganizationRating, OrganizationStaff, StaffRole
from .permissions import HasOrgPrivilege, IsOrgAdminOfOrg
from .privileges import STAFF_PRIVILEGES
from .serializers import (
    OrganizationRatingSerializer,
    OrganizationSerializer,
    OrganizationStaffSerializer,
    StaffInviteAcceptSerializer,
    StaffRoleSerializer,
)
from .services import (
    InviteError,
    InviteExpiredError,
    InviteInvalidError,
    accept_invite,
    create_or_invite_staff,
    create_staff_with_credentials,
    invite_link,
    rate_organization,
    resend_staff_invite,
    resolve_invite,
)


def _rating_annotations():
    """Avg/count of ratings as subqueries — joining `ratings` alongside the
    `submissions` joins in org_queryset_with_counts would cross-multiply rows
    and skew the aggregates, so keep ratings out of the main join tree."""
    base = OrganizationRating.objects.filter(organization=OuterRef('pk')).values('organization')
    return {
        'average_rating_annotated': Subquery(base.annotate(avg=Avg('score')).values('avg')),
        'rating_count_annotated': Coalesce(
            Subquery(base.annotate(cnt=Count('pk')).values('cnt'), output_field=IntegerField()),
            0,
        ),
    }


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
        **_rating_annotations(),
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


class OrganizationShowcaseView(generics.ListAPIView):
    """GET /organizations/{slug}/showcase/ — public list of submissions this
    organization's staff have chosen to showcase (Submission.is_public=True).

    AllowAny, like OrganizationDetailView — an org's public profile (and its
    showcase) is reachable by slug regardless of verification status, same as
    today; verification only gates whether the org appears in *search/browse*
    results (OrganizationListCreateView), not direct access.

    Reuses TrackSubmissionSerializer: it already never exposes submitter
    contact details and shows 'Anonymous' in place of a name for anonymous
    submissions — exactly the redaction a public showcase needs.
    """

    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        from apps.submissions.serializers import TrackSubmissionSerializer
        return TrackSubmissionSerializer

    def get_queryset(self):
        from apps.submissions.models import Submission
        org = get_object_or_404(Organization, slug=self.kwargs['slug'], is_active=True)
        return (
            Submission.objects.filter(organization=org, is_public=True)
            .select_related('organization', 'category', 'citizen')
            .prefetch_related('updates__updated_by')
        )


class MyOrganizationView(APIView):
    """GET /organizations/mine/ — the organization managed by the current user."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        org = org_queryset_with_counts().filter(admin=request.user).first()
        if org is None:
            return Response({'detail': 'You do not manage any organization.'}, status=404)
        return Response(OrganizationSerializer(org, context={'request': request}).data)


class OrganizationRatingView(APIView):
    """GET/PUT/DELETE /organizations/{slug}/rating/ — the current user's own rating.

    PUT upserts (one rating per user per org — re-rating overwrites), GET
    returns `{score: null}` when the user hasn't rated yet, DELETE withdraws
    the rating. The public *average* is never served here; it rides on the
    organization serializer / locations endpoint, subject to `show_rating`.
    """

    permission_classes = [permissions.IsAuthenticated]

    def _get_org(self, slug):
        return get_object_or_404(Organization, slug=slug, is_active=True)

    def get(self, request, slug):
        org = self._get_org(slug)
        rating = OrganizationRating.objects.filter(organization=org, user=request.user).first()
        return Response({'score': rating.score if rating else None})

    def put(self, request, slug):
        org = self._get_org(slug)
        serializer = OrganizationRatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rating = rate_organization(org, request.user, serializer.validated_data['score'])
        return Response({'score': rating.score})

    def delete(self, request, slug):
        org = self._get_org(slug)
        OrganizationRating.objects.filter(organization=org, user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrganizationLocationsView(APIView):
    """GET /organizations/locations/ — public, unpaginated map payload.

    Only active, verified organizations that have both coordinates set.
    Deliberately lightweight (no description/contact fields) since the map
    may load every organization at once; `average_rating`/`rating_count`
    are nulled when the org opted out of public ratings.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        orgs = Organization.objects.filter(
            is_active=True, is_verified=True,
            latitude__isnull=False, longitude__isnull=False,
        ).annotate(**_rating_annotations()).order_by('name')

        return Response([
            {
                'name': org.name,
                'slug': org.slug,
                'category': org.category,
                'latitude': float(org.latitude),
                'longitude': float(org.longitude),
                'average_rating': (
                    round(float(org.average_rating_annotated), 1)
                    if org.show_rating and org.average_rating_annotated is not None else None
                ),
                'rating_count': org.rating_count_annotated if org.show_rating else None,
            }
            for org in orgs
        ])


class OrganizationSettingsView(APIView):
    """PATCH /organizations/{slug}/settings/ — edit the organization's own profile
    fields (name, description, category, logo, website, contact info, address).

    Requires org admin, platform staff, or the 'manage_org_profile' privilege.
    """

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, slug):
        org = get_object_or_404(Organization, slug=slug)
        HasOrgPrivilege('manage_org_profile').check(request, org)
        serializer = OrganizationSerializer(
            org, data=request.data, partial=True, context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class OrganizationSubmissionsView(generics.ListAPIView):
    """GET /organizations/{slug}/submissions/ — org admin or 'view_submissions' privilege."""

    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'priority', 'submission_type']

    def get_serializer_class(self):
        from apps.submissions.serializers import SubmissionSerializer
        return SubmissionSerializer

    def get_queryset(self):
        from apps.submissions.models import Submission
        org = get_object_or_404(Organization, slug=self.kwargs['slug'])
        HasOrgPrivilege('view_submissions').check(self.request, org)
        qs = (
            Submission.objects.filter(organization=org)
            .select_related('organization', 'category', 'citizen')
            .prefetch_related('updates__updated_by')
        )
        # ?assigned_to=me — the current user's own queue on the staff
        # dashboard. Any other value is left to the standard status/priority/
        # submission_type filterset (no generic numeric-id lookup is exposed
        # here to avoid leaking other staff members' assignment counts).
        if self.request.query_params.get('assigned_to') == 'me':
            qs = qs.filter(assigned_to__user=self.request.user, assigned_to__organization=org)
        return qs


class OrganizationStatsView(APIView):
    """GET /organizations/{slug}/stats/ — org admin or 'view_stats' privilege."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, slug):
        from apps.submissions.services import organization_stats
        org = get_object_or_404(Organization, slug=slug)
        HasOrgPrivilege('view_stats').check(request, org)
        return Response(organization_stats(org))


class OrganizationPrivilegesView(APIView):
    """GET /organizations/privileges/ — static catalog of assignable staff privileges.

    This carries no org-specific data (see apps/organizations/privileges.py) so
    it is safe to expose to anyone authenticated — least-restrictive option
    that still avoids handing the catalog to fully anonymous callers.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(STAFF_PRIVILEGES)


class OrganizationRolesView(generics.ListCreateAPIView):
    """GET /organizations/{slug}/roles/ — list custom roles; POST — create one.

    Requires org admin or the 'manage_roles' privilege.
    """

    serializer_class = StaffRoleSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def _get_org(self):
        if not hasattr(self, '_org'):
            org = get_object_or_404(Organization, slug=self.kwargs['slug'])
            HasOrgPrivilege('manage_roles').check(self.request, org)
            self._org = org
        return self._org

    def get_queryset(self):
        return (
            StaffRole.objects.filter(organization=self._get_org())
            .annotate(staff_count_annotated=Count('staff_members', distinct=True))
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['organization'] = self._get_org()
        return context


class OrganizationRoleDetailView(APIView):
    """PATCH/DELETE /organizations/{slug}/roles/{role_id}/ — update or delete a custom role.

    Requires org admin or the 'manage_roles' privilege.
    """

    permission_classes = [permissions.IsAuthenticated]

    def _get_objects(self, request, slug, role_id):
        org = get_object_or_404(Organization, slug=slug)
        HasOrgPrivilege('manage_roles').check(request, org)
        role = get_object_or_404(
            StaffRole.objects.annotate(staff_count_annotated=Count('staff_members', distinct=True)),
            pk=role_id, organization=org,
        )
        return org, role

    def patch(self, request, slug, role_id):
        org, role = self._get_objects(request, slug, role_id)
        serializer = StaffRoleSerializer(
            role, data=request.data, partial=True, context={'organization': org},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, slug, role_id):
        _, role = self._get_objects(request, slug, role_id)
        if role.staff_members.exists():
            return Response(
                {'detail': 'Cannot delete a role that still has staff members assigned to it.'},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            role.delete()
        except ProtectedError:
            return Response(
                {'detail': 'Cannot delete a role that still has staff members assigned to it.'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyStaffAccessView(APIView):
    """GET /organizations/my-access/ — the current user's active org-staff role & privileges.

    Design decision (staff-roles-privileges subtask 05): this is a **dedicated
    endpoint** rather than an addition to `UserSerializer`/`GET /auth/me/`.
    `UserSerializer.organization_name`/`organization_slug` already answer "does
    this user manage an org as `org_admin`?" — that flow is left untouched.
    This endpoint answers the separate question "is this user an *active*
    OrganizationStaff member somewhere, and what can they do?", which matters
    because staff members never get `user_type` promoted to `org_admin` (see
    CLAUDE.md section 4) — without this endpoint the frontend has no way to
    grant them staff-scoped access. Keeping the two responses separate means a
    user who happens to be both an org_admin of one org and a staff member of
    another never has those two relationships conflated into one payload.

    Only the requesting user's own membership is ever resolved (`user=request.user`);
    invited-but-unaccepted and disabled staff rows are deliberately excluded so
    they read as "no access" rather than an error. Always returns 200 — a user
    with no qualifying membership gets null/empty fields, not a 404.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        staff = (
            OrganizationStaff.objects.filter(
                user=request.user, status='active', is_active=True,
            )
            .select_related('organization', 'role')
            .first()
        )
        if staff is None:
            return Response({
                'organization_name': None,
                'organization_slug': None,
                'role_name': None,
                'privileges': [],
            })
        return Response({
            'organization_name': staff.organization.name,
            'organization_slug': staff.organization.slug,
            'role_name': staff.role.name if staff.role else None,
            'privileges': (staff.role.privileges or []) if staff.role else [],
        })


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

    def _resolve_role(self, org, role_id):
        if role_id in (None, ''):
            raise ValidationError({'role': 'This field is required.'})
        try:
            return StaffRole.objects.get(pk=role_id, organization=org)
        except (StaffRole.DoesNotExist, ValueError, TypeError):
            raise ValidationError({'role': 'Invalid role for this organization.'})

    def post(self, request, slug):
        """Add a staff member — two mutually exclusive modes, chosen by `mode`:

        - `mode: 'invite'` (default) — by email. An existing, already-usable-
          password user is attached immediately (status='active'); otherwise a
          pending user is created and a single-use, expiring invite link is
          emailed. See services.create_or_invite_staff.
        - `mode: 'credentials'` — admin sets `username`/`password`/`email`
          directly; the account is active immediately with
          must_change_password=True and email_verified=False. See
          services.create_staff_with_credentials.
        """
        org = self._get_org()
        mode = request.data.get('mode', 'invite')

        if mode == 'credentials':
            role = self._resolve_role(org, request.data.get('role'))
            staff = create_staff_with_credentials(
                org=org,
                username=request.data.get('username', ''),
                password=request.data.get('password', ''),
                email=request.data.get('email', ''),
                role=role,
                assigned_by=request.user,
            )
            data = OrganizationStaffSerializer(staff).data
            data['invited'] = False
            data['invite_link'] = None
            return Response(data, status=status.HTTP_201_CREATED)

        user_email = (request.data.get('user_email') or '').strip().lower()
        if not user_email:
            raise ValidationError({'user_email': 'This field is required.'})
        role = self._resolve_role(org, request.data.get('role'))

        staff, invited, raw_token = create_or_invite_staff(
            org=org, email=user_email, role=role, assigned_by=request.user,
        )
        data = OrganizationStaffSerializer(staff).data
        data['invited'] = invited
        # Copy-link fallback for when email delivery isn't configured/reachable —
        # safe to return since only the inviting admin sees this response.
        data['invite_link'] = invite_link(raw_token) if raw_token else None
        return Response(data, status=status.HTTP_201_CREATED)


class OrganizationStaffResendInviteView(APIView):
    """POST /organizations/{slug}/staff/{staff_id}/resend-invite/

    Invalidates any prior unaccepted token for this staff row and issues +
    emails a new one. Requires org admin or the 'manage_staff' privilege.
    Returns 400 if the staff member's status is already 'active'
    (see services.resend_staff_invite).
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug, staff_id):
        org = get_object_or_404(Organization, slug=slug)
        HasOrgPrivilege('manage_staff').check(request, org)
        staff = get_object_or_404(OrganizationStaff, pk=staff_id, organization=org)
        staff, raw_token = resend_staff_invite(staff, request.user)
        data = OrganizationStaffSerializer(staff).data
        data['invite_link'] = invite_link(raw_token)
        return Response(data)


class StaffInvitePreviewView(APIView):
    """GET /organizations/invite/<token>/ — public preview of a pending invite.

    Returns just enough to render a "You're invited to join <org> as <role>"
    screen before the user sets a password. An invalid, expired, or
    already-accepted token returns a bare 404 (never a distinguishing error)
    so nothing about other invites is enumerable.
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def get(self, request, token):
        try:
            invite = resolve_invite(token)
        except InviteError:
            raise NotFound()

        staff = invite.staff
        return Response({
            'organization': staff.organization.name,
            'organization_slug': staff.organization.slug,
            'role': staff.role.name if staff.role else None,
            'email': staff.user.email,
        })


class StaffInviteAcceptView(APIView):
    """POST /organizations/invite/<token>/accept/ — set a password and log in.

    Validates the token, validates the new password with Django's password
    validators (StaffInviteAcceptSerializer, mirroring
    UserRegistrationSerializer.validate), activates the user, marks the staff
    row active, and returns the same {access, user} shape (plus refresh
    cookie) as RegisterView so the frontend can reuse its session-setting logic.

    An expired token returns 410 with an 'expired' message; any other
    unusable token (invalid or already accepted) returns 400 — neither leaks
    enough to enumerate other invites.
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request, token):
        try:
            invite = resolve_invite(token)
        except InviteExpiredError as exc:
            return Response({'detail': exc.message}, status=status.HTTP_410_GONE)
        except InviteInvalidError as exc:
            return Response({'detail': exc.message}, status=status.HTTP_400_BAD_REQUEST)

        serializer = StaffInviteAcceptSerializer(
            data=request.data, context={'user': invite.staff.user},
        )
        serializer.is_valid(raise_exception=True)

        user = accept_invite(invite, serializer.validated_data['password'])
        payload = _auth_payload(user)
        response = Response({'access': payload['access'], 'user': payload['user']})
        _set_refresh_cookie(response, payload['refresh'])
        return response


class OrganizationStaffDetailView(APIView):
    """PATCH/DELETE /organizations/{slug}/staff/{staff_id}/ — update role or remove staff."""

    permission_classes = [permissions.IsAuthenticated]

    def _get_objects(self, request, slug, staff_id):
        org = get_object_or_404(Organization, slug=slug)
        IsOrgAdminOfOrg().check(request, org)
        staff = get_object_or_404(OrganizationStaff, pk=staff_id, organization=org)
        return org, staff

    def patch(self, request, slug, staff_id):
        org, staff = self._get_objects(request, slug, staff_id)
        serializer = OrganizationStaffSerializer(
            staff, data=request.data, partial=True, context={'organization': org},
        )
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
