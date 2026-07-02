from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import Organization
from .serializers import OrganizationSerializer


class OrganizationListCreateView(generics.ListCreateAPIView):
    serializer_class = OrganizationSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.user_type == 'org_admin':
            return Organization.objects.filter(
                Q(is_verified=True) | Q(admin=user)
            )
        return Organization.objects.filter(is_verified=True)


class OrganizationDetailView(generics.RetrieveAPIView):
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'
    queryset = Organization.objects.all()


class OrganizationSubmissionsView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        from apps.submissions.serializers import SubmissionSerializer
        return SubmissionSerializer

    def get_queryset(self):
        from apps.submissions.models import Submission
        org = get_object_or_404(Organization, slug=self.kwargs['slug'])
        if self.request.user != org.admin and not self.request.user.is_staff:
            raise PermissionDenied('Only this organization\'s admin can view its submissions.')
        return Submission.objects.filter(organization=org).order_by('-created_at')


class OrganizationStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, slug):
        from apps.submissions.models import Submission
        org = get_object_or_404(Organization, slug=slug)

        if request.user != org.admin and not request.user.is_staff:
            return Response(
                {'detail': 'Only this organization\'s admin can view stats.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        submissions = Submission.objects.filter(organization=org)

        by_status = {s: submissions.filter(status=s).count() for s, _ in Submission.STATUS_CHOICES}
        by_type = {t: submissions.filter(submission_type=t).count() for t, _ in Submission.TYPE_CHOICES}
        by_priority = {
            p: submissions.filter(priority=p).count()
            for p in ['low', 'medium', 'high', 'urgent']
        }

        return Response({
            'organization': org.name,
            'total': submissions.count(),
            'by_status': by_status,
            'by_type': by_type,
            'by_priority': by_priority,
        })
