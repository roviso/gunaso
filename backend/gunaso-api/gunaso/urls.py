from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/organizations/', include('apps.organizations.urls')),
    path('api/v1/categories/', include('apps.submissions.category_urls')),
    path('api/v1/submissions/', include('apps.submissions.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
