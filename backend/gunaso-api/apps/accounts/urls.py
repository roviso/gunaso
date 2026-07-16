from django.urls import path

from .views import (
    ChangePasswordView,
    ConfirmEmailVerificationView,
    LoginView,
    LogoutView,
    MeView,
    RefreshView,
    RegisterView,
    RequestEmailVerificationView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('refresh/', RefreshView.as_view(), name='auth-token-refresh'),
    path('token/refresh/', RefreshView.as_view(), name='auth-token-refresh-alias'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('me/', MeView.as_view(), name='auth-me'),
    path('change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
    path('email-verification/request/', RequestEmailVerificationView.as_view(), name='auth-email-verify-request'),
    path('email-verification/confirm/', ConfirmEmailVerificationView.as_view(), name='auth-email-verify-confirm'),
]
