from django.conf import settings
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView


def password_reset_redirect(request, uid, token):
    """
    Email links use the Django Site domain; this sends users to the SPA reset page.
    """
    base = getattr(settings, "FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")
    return redirect(f"{base}/password-reset/{uid}/{token}/")


def activation_redirect(request, uid, token):
    """
    Activation emails link to the API host; redirect to the SPA activation route.
    """
    base = getattr(settings, "FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")
    return redirect(f"{base}/activate/{uid}/{token}/")


# Serve Vue Application
index_view = never_cache(TemplateView.as_view(template_name="index.html"))

# Serve robot.txt from vue
robots = never_cache(TemplateView.as_view(template_name="robots.txt"))
