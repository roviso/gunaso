from django.urls import path

from .views import OrgAdminStatsView, OrgAdminSubmissionsView, OrgAIReportsView, OrgMapFeedView

urlpatterns = [
    path('submissions/', OrgAdminSubmissionsView.as_view(), name='org-admin-submissions'),
    path('stats/', OrgAdminStatsView.as_view(), name='org-admin-stats'),
    path('ai-reports/', OrgAIReportsView.as_view(), name='org-ai-reports'),
    path('map-feed/', OrgMapFeedView.as_view(), name='org-map-feed'),
]
