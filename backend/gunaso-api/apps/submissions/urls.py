from django.urls import path, re_path

from .views import (
    MySubmissionsView,
    SubmissionAIClassifyView,
    SubmissionAISuggestionView,
    SubmissionAssignView,
    SubmissionCategoryUpdateView,
    SubmissionCreateView,
    SubmissionDetailView,
    SubmissionStatusUpdateView,
    SubmissionUpdatesView,
    SubmissionVisibilityView,
    TrackSubmissionView,
)

urlpatterns = [
    path('', SubmissionCreateView.as_view(), name='submission-create'),
    path('my/', MySubmissionsView.as_view(), name='submission-my'),
    re_path(
        r'^track/(?P<reference_number>[A-Za-z0-9\-]+)/$',
        TrackSubmissionView.as_view(),
        name='submission-track',
    ),
    path('<str:reference_number>/', SubmissionDetailView.as_view(), name='submission-detail'),
    path('<str:reference_number>/status/', SubmissionStatusUpdateView.as_view(), name='submission-status'),
    path('<str:reference_number>/updates/', SubmissionUpdatesView.as_view(), name='submission-updates'),
    path('<str:reference_number>/assign/', SubmissionAssignView.as_view(), name='submission-assign'),
    path('<str:reference_number>/visibility/', SubmissionVisibilityView.as_view(), name='submission-visibility'),
    path('<str:reference_number>/category/', SubmissionCategoryUpdateView.as_view(), name='submission-category'),
    path('<str:reference_number>/ai-classify/', SubmissionAIClassifyView.as_view(), name='submission-ai-classify'),
    path('<str:reference_number>/ai-suggestion/', SubmissionAISuggestionView.as_view(), name='submission-ai-suggestion'),
]
