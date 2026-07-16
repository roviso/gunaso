from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    ChangePasswordSerializer,
    EmailVerificationRequestSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)
from .services import (
    EmailVerificationError,
    generate_email_verification_token,
    resolve_email_verification_token,
    send_verification_email,
)

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
    """POST /auth/login/ — email-or-username + password login; refresh token
    goes into an httpOnly cookie.

    The `email` field accepts either an email address or a username — this
    lets staff log in with the username an org admin assigned them (see
    apps/organizations/services.py::create_staff_with_credentials) without
    changing the request payload shape self-registered users already use.
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        identifier = (request.data.get('email') or '').strip()
        password = request.data.get('password') or ''
        if not identifier or not password:
            return Response(
                {'detail': 'Email and password are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(
            Q(email__iexact=identifier) | Q(username__iexact=identifier),
        ).first()
        authenticated = (
            authenticate(request, username=user.username, password=password) if user else None
        )
        if authenticated is None or not authenticated.is_active:
            # Same message regardless of which lookup failed — no account enumeration.
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


class ChangePasswordView(APIView):
    """POST /auth/change-password/ — set a new password for the current session.

    Doubles as the forced first-login flow for admin-created staff accounts
    (User.must_change_password): on success the flag is always cleared, so
    the frontend's forced-change guard only ever needs to check the boolean
    already present on the login/me payload.
    """

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'user': request.user})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.must_change_password = False
        user.save(update_fields=['password', 'must_change_password'])

        return Response({'user': UserSerializer(user).data})


class RequestEmailVerificationView(APIView):
    """POST /auth/email-verification/request/ — email the current user a
    single-use verification link, optionally correcting the address first.

    Lets a staff member fix an admin-typo'd email in the same step as
    verifying it (EmailVerificationRequestSerializer), rather than needing a
    separate profile-edit round trip first.
    """

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        if request.user.email_verified:
            raise ValidationError({'detail': 'Your email is already verified.'})

        serializer = EmailVerificationRequestSerializer(
            data=request.data, context={'user': request.user},
        )
        serializer.is_valid(raise_exception=True)

        new_email = serializer.validated_data.get('email')
        if new_email and new_email != request.user.email:
            request.user.email = new_email
            request.user.save(update_fields=['email'])

        token = generate_email_verification_token(request.user)
        send_verification_email(request.user, token)
        return Response({'detail': 'Verification email sent.', 'email': request.user.email})


class ConfirmEmailVerificationView(APIView):
    """POST /auth/email-verification/confirm/ — mark the token's email as
    verified. Public (AllowAny): the link may be opened on a device/session
    other than the one currently signed in, mirroring the staff invite accept
    endpoint's reasoning."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        token = request.data.get('token') or ''
        try:
            user = resolve_email_verification_token(token)
        except EmailVerificationError as exc:
            return Response({'detail': exc.message}, status=status.HTTP_400_BAD_REQUEST)

        user.email_verified = True
        user.save(update_fields=['email_verified'])
        return Response({'detail': 'Email verified.'})
