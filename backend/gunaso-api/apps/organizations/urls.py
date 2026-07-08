from django.urls import path

from .views import (
    MyOrganizationView,
    OrganizationDetailView,
    OrganizationListCreateView,
    OrganizationQRCodeView,
    OrganizationStaffDetailView,
    OrganizationStaffView,
    OrganizationStatsView,
    OrganizationSubmissionsView,
)

urlpatterns = [
    path('', OrganizationListCreateView.as_view(), name='organization-list'),
    path('mine/', MyOrganizationView.as_view(), name='organization-mine'),
    path('<slug:slug>/', OrganizationDetailView.as_view(), name='organization-detail'),
    path('<slug:slug>/submissions/', OrganizationSubmissionsView.as_view(), name='org-submissions'),
    path('<slug:slug>/stats/', OrganizationStatsView.as_view(), name='org-stats'),
    path('<slug:slug>/staff/', OrganizationStaffView.as_view(), name='org-staff'),
    path('<slug:slug>/staff/<int:staff_id>/', OrganizationStaffDetailView.as_view(), name='org-staff-detail'),
    path('<slug:slug>/qrcode/', OrganizationQRCodeView.as_view(), name='org-qrcode'),
]
