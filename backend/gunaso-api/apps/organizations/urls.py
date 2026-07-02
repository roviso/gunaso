from django.urls import path
from .views import (
    OrganizationListCreateView,
    OrganizationDetailView,
    OrganizationSubmissionsView,
    OrganizationStatsView,
)

urlpatterns = [
    path('', OrganizationListCreateView.as_view(), name='organization-list'),
    path('<slug:slug>/', OrganizationDetailView.as_view(), name='organization-detail'),
    path('<slug:slug>/submissions/', OrganizationSubmissionsView.as_view(), name='org-submissions'),
    path('<slug:slug>/stats/', OrganizationStatsView.as_view(), name='org-stats'),
]
