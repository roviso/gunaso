from django.urls import path

from .views import (
    AdminAuditLogListView,
    AdminOrganizationActionView,
    AdminOrganizationListView,
    AdminOrganizationStaffView,
    AdminOverviewView,
    AdminSubmissionListView,
    AdminUserBlockView,
    AdminUserDemoteView,
    AdminUserListView,
    AdminUserPromoteView,
    AdminUserUnblockView,
)

urlpatterns = [
    path('overview/', AdminOverviewView.as_view(), name='admin-overview'),
    path('organizations/', AdminOrganizationListView.as_view(), name='admin-organization-list'),
    path('organizations/<slug:slug>/', AdminOrganizationActionView.as_view(), name='admin-organization-action'),
    path('organizations/<slug:slug>/staff/', AdminOrganizationStaffView.as_view(), name='admin-organization-staff'),
    path('users/', AdminUserListView.as_view(), name='admin-user-list'),
    path('users/<int:user_id>/block/', AdminUserBlockView.as_view(), name='admin-user-block'),
    path('users/<int:user_id>/unblock/', AdminUserUnblockView.as_view(), name='admin-user-unblock'),
    path('users/<int:user_id>/promote/', AdminUserPromoteView.as_view(), name='admin-user-promote'),
    path('users/<int:user_id>/demote/', AdminUserDemoteView.as_view(), name='admin-user-demote'),
    path('submissions/', AdminSubmissionListView.as_view(), name='admin-submission-list'),
    path('audit-log/', AdminAuditLogListView.as_view(), name='admin-audit-log'),
]
