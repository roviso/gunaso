from django.urls import path

from .views import (
    MyOrganizationView,
    MyStaffAccessView,
    OrganizationDetailView,
    OrganizationListCreateView,
    OrganizationLocationsView,
    OrganizationPrivilegesView,
    OrganizationQRCodeView,
    OrganizationRatingView,
    OrganizationRoleDetailView,
    OrganizationRolesView,
    OrganizationSettingsView,
    OrganizationShowcaseView,
    OrganizationStaffDetailView,
    OrganizationStaffResendInviteView,
    OrganizationStaffView,
    OrganizationStatsView,
    OrganizationSubmissionsView,
    StaffInviteAcceptView,
    StaffInvitePreviewView,
)

urlpatterns = [
    path('', OrganizationListCreateView.as_view(), name='organization-list'),
    path('mine/', MyOrganizationView.as_view(), name='organization-mine'),
    path('my-access/', MyStaffAccessView.as_view(), name='organization-my-access'),
    path('privileges/', OrganizationPrivilegesView.as_view(), name='org-privileges'),
    path('locations/', OrganizationLocationsView.as_view(), name='org-locations'),
    # Static prefixes before the single-segment <slug:slug> catch-all — Django
    # matches urlpatterns in order, and while the slug converter never spans a
    # '/' (so it can't shadow these multi-segment paths), keeping them grouped
    # here avoids ambiguity as more static routes are added.
    path('invite/<str:token>/', StaffInvitePreviewView.as_view(), name='org-invite-preview'),
    path('invite/<str:token>/accept/', StaffInviteAcceptView.as_view(), name='org-invite-accept'),
    path('<slug:slug>/', OrganizationDetailView.as_view(), name='organization-detail'),
    path('<slug:slug>/settings/', OrganizationSettingsView.as_view(), name='org-settings'),
    path('<slug:slug>/rating/', OrganizationRatingView.as_view(), name='org-rating'),
    path('<slug:slug>/submissions/', OrganizationSubmissionsView.as_view(), name='org-submissions'),
    path('<slug:slug>/showcase/', OrganizationShowcaseView.as_view(), name='org-showcase'),
    path('<slug:slug>/stats/', OrganizationStatsView.as_view(), name='org-stats'),
    path('<slug:slug>/staff/', OrganizationStaffView.as_view(), name='org-staff'),
    path('<slug:slug>/staff/<int:staff_id>/', OrganizationStaffDetailView.as_view(), name='org-staff-detail'),
    path(
        '<slug:slug>/staff/<int:staff_id>/resend-invite/',
        OrganizationStaffResendInviteView.as_view(),
        name='org-staff-resend-invite',
    ),
    path('<slug:slug>/roles/', OrganizationRolesView.as_view(), name='org-roles'),
    path('<slug:slug>/roles/<int:role_id>/', OrganizationRoleDetailView.as_view(), name='org-role-detail'),
    path('<slug:slug>/qrcode/', OrganizationQRCodeView.as_view(), name='org-qrcode'),
]
