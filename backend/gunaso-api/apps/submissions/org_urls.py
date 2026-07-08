from django.urls import path

from .views import OrgAdminStatsView, OrgAdminSubmissionsView

urlpatterns = [
    path('submissions/', OrgAdminSubmissionsView.as_view(), name='org-admin-submissions'),
    path('stats/', OrgAdminStatsView.as_view(), name='org-admin-stats'),
]
