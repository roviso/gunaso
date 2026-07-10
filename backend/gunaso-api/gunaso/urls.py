from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.core import views as core_views


def health_check(request):
    """Liveness/readiness probe: verifies the database connection."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        return JsonResponse({'status': 'ok'})
    except Exception:
        return JsonResponse({'status': 'error', 'detail': 'database unavailable'}, status=503)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/health/', health_check, name='health-check'),
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/organizations/', include('apps.organizations.urls')),
    path('api/v1/categories/', include('apps.submissions.category_urls')),
    path('api/v1/submissions/', include('apps.submissions.urls')),
    path('api/v1/org/', include('apps.submissions.org_urls')),
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

"""
Generates a regex with reverse lookup of urls including static an>
This regex is then used in re_path of Vue's index.html.
This is done to handle any django url without a trailing slash.
"""

urls = list()
if settings.STATIC_URL:
    static_url = settings.STATIC_URL
    if static_url != "/":
        static_url = static_url.strip("/")

    urls.append(static_url)
if settings.MEDIA_URL:
    media_url = settings.MEDIA_URL
    if media_url != "/":
        media_url = media_url.strip("/")
    urls.append(media_url)
for url in urlpatterns:
    if "proxy" in str(url.pattern):
        urls.append("proxy")
    else:
        urls.append(str(url.pattern).strip("/"))
pattern_base = f'(?!{"|".join(urls)})'
pattern_index = f"^{pattern_base}.*$"
urlpatterns += [
    re_path(pattern_index, core_views.index_view, name="Home"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
