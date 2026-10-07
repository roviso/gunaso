from django.urls import path

from .views import PublicStatsView, PublicStoriesView

urlpatterns = [
    path('stats/', PublicStatsView.as_view(), name='public-stats'),
    path('stories/', PublicStoriesView.as_view(), name='public-stories'),
]
