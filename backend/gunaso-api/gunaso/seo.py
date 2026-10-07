"""robots.txt and sitemap.xml for the public SPA pages.

Served by Django (not the Vue build) so the sitemap can list every verified
organization's public profile. All URLs point at FRONTEND_URL — the SPA's
origin, same rule as emailed links.
"""
from xml.sax.saxutils import escape

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.cache import cache_page

# Public, indexable SPA routes. Dashboards, auth flows and per-submission
# track pages are deliberately left out (and disallowed in robots.txt).
STATIC_PAGES = [
    ('/', 'daily', '1.0'),
    ('/organizations', 'daily', '0.9'),
    ('/map', 'daily', '0.8'),
    ('/submit', 'monthly', '0.9'),
    ('/track', 'monthly', '0.6'),
    ('/for-organizations', 'monthly', '0.8'),
    ('/how-it-works', 'monthly', '0.7'),
    ('/contact', 'yearly', '0.5'),
    ('/privacy', 'yearly', '0.3'),
    ('/terms', 'yearly', '0.3'),
]


def _base() -> str:
    return getattr(settings, 'FRONTEND_URL', 'http://localhost:3000').rstrip('/')


@cache_page(60 * 60)
def robots_txt(request):
    lines = [
        'User-agent: *',
        'Disallow: /api/',
        'Disallow: /django-admin/',
        'Disallow: /admin',
        'Disallow: /org/',
        'Disallow: /dashboard',
        'Disallow: /track/',
        'Disallow: /invite/',
        'Disallow: /reset-password/',
        'Disallow: /verify-email/',
        '',
        f'Sitemap: {_base()}/sitemap.xml',
        '',
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain; charset=utf-8')


@cache_page(60 * 60)
def sitemap_xml(request):
    from apps.organizations.models import Organization

    base = _base()
    urls = [
        f'<url><loc>{escape(base + path)}</loc><changefreq>{freq}</changefreq><priority>{prio}</priority></url>'
        for path, freq, prio in STATIC_PAGES
    ]
    orgs = Organization.objects.filter(is_active=True, is_verified=True).only('slug', 'updated_at')
    for org in orgs:
        urls.append(
            f'<url><loc>{escape(f"{base}/organizations/{org.slug}")}</loc>'
            f'<lastmod>{org.updated_at.date().isoformat()}</lastmod>'
            '<changefreq>weekly</changefreq><priority>0.7</priority></url>'
        )
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + ''.join(urls)
        + '</urlset>\n'
    )
    return HttpResponse(body, content_type='application/xml; charset=utf-8')
