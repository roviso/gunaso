from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from rest_framework import generics, permissions, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import UserRegistrationSerializer, UserSerializer

User = get_user_model()


def _set_refresh_cookie(response, refresh_token: str) -> None:
    """Store the refresh token in an httpOnly cookie, scoped to the auth URLs."""
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE,
        refresh_token,
        max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
        path=settings.JWT_REFRESH_COOKIE_PATH,
        httponly=True,
        secure=not settings.DEBUG,
        samesite='Lax',
    )


def _clear_refresh_cookie(response) -> None:
    response.delete_cookie(settings.JWT_REFRESH_COOKIE, path=settings.JWT_REFRESH_COOKIE_PATH)


def _auth_payload(user) -> dict:
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserSerializer(user).data,
    }


class RegisterView(APIView):
    """POST /auth/register/ — create an account and log the user in."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        payload = _auth_payload(user)
        response = Response(
            {'access': payload['access'], 'user': payload['user']},
            status=status.HTTP_201_CREATED,
        )
        _set_refresh_cookie(response, payload['refresh'])
        return response


class LoginView(APIView):
    """POST /auth/login/ — email + password login; refresh token goes into an httpOnly cookie."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        email = (request.data.get('email') or '').lower().strip()
        password = request.data.get('password') or ''
        if not email or not password:
            return Response(
                {'detail': 'Email and password are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(email__iexact=email).first()
        authenticated = (
            authenticate(request, username=user.username, password=password) if user else None
        )
        if authenticated is None or not authenticated.is_active:
            # Same message whether the email exists or not — no account enumeration.
            raise AuthenticationFailed('Invalid email or password.')

        payload = _auth_payload(authenticated)
        response = Response({'access': payload['access'], 'user': payload['user']})
        _set_refresh_cookie(response, payload['refresh'])
        return response


class RefreshView(APIView):
    """POST /auth/refresh/ — rotate the refresh cookie, return a new access token."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        raw_token = request.COOKIES.get(settings.JWT_REFRESH_COOKIE) or request.data.get('refresh')
        if not raw_token:
            return Response(
                {'detail': 'No refresh token provided.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            refresh = RefreshToken(raw_token)
            user = User.objects.get(id=refresh.payload.get('user_id'), is_active=True)
            refresh.blacklist()
            new_refresh = RefreshToken.for_user(user)
        except (TokenError, User.DoesNotExist):
            response = Response(
                {'detail': 'Invalid or expired refresh token.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            _clear_refresh_cookie(response)
            return response

        response = Response({
            'access': str(new_refresh.access_token),
            'user': UserSerializer(user).data,
        })
        _set_refresh_cookie(response, str(new_refresh))
        return response


class LogoutView(APIView):
    """POST /auth/logout/ — blacklist the refresh token and clear the cookie."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        raw_token = request.COOKIES.get(settings.JWT_REFRESH_COOKIE) or request.data.get('refresh')
        if raw_token:
            try:
                RefreshToken(raw_token).blacklist()
            except TokenError:
                pass
        response = Response({'detail': 'Logged out.'})
        _clear_refresh_cookie(response)
        return response


class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /auth/me/ — the authenticated user's own profile."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
