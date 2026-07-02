from django.urls import path
from .views import (
    SubmissionListCreateView,
    SubmissionDetailView,
    SubmissionStatusUpdateView,
    SubmissionUpdatesView,
)

urlpatterns = [
    path('', SubmissionListCreateView.as_view(), name='submission-list'),
    path('<str:reference_number>/', SubmissionDetailView.as_view(), name='submission-detail'),
    path('<str:reference_number>/status/', SubmissionStatusUpdateView.as_view(), name='submission-status'),
    path('<str:reference_number>/updates/', SubmissionUpdatesView.as_view(), name='submission-updates'),
]
