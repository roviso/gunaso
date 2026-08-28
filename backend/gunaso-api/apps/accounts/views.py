import logging

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
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)
from .services import (
    EmailVerificationError,
    PasswordResetError,
    generate_email_verification_token,
    request_password_reset,
    reset_password,
    resolve_email_verification_token,
    resolve_password_reset_token,
    send_verification_email,
)

User = get_user_model()
logger = logging.getLogger(__name__)


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


class PasswordResetRequestView(APIView):
    """POST /auth/password-reset/ — email a reset link to the address given.

    Always answers 200 with the same body, whether or not an account matched.
    Anything else (404, a different message, a different latency class) would
    turn this endpoint into an account-enumeration oracle, which CLAUDE.md
    section 8 rules out for login and applies here for the same reason.

    Throttled on the shared 'auth' scope so it can't be used to spray mail from
    the platform's SMTP identity.
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            request_password_reset(serializer.validated_data['email'])
        except Exception:
            # A dead/misconfigured SMTP host must not tell the caller whether
            # the address exists either, and must not surface an opaque 500
            # for what is, to the user, a routine action. Details go to the
            # server log only (CLAUDE.md section 9).
            logger.exception('Password reset email could not be sent.')

        return Response({
            'detail': 'If an account exists for that email, a password reset link has been sent.',
        })


class PasswordResetConfirmView(APIView):
    """POST /auth/password-reset/confirm/ — set a new password from a reset link.

    Public by design: the link is opened from an email client, on a device with
    no session — the uid/token pair is the credential. Same reasoning as the
    staff-invite accept and email-verification confirm endpoints.
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        # Resolved before the serializer runs so the password validators can be
        # bound to the actual target user (UserAttributeSimilarityValidator
        # needs it), and so a bad link fails with one clear message rather than
        # per-field noise.
        try:
            user = resolve_password_reset_token(
                request.data.get('uid') or '', request.data.get('token') or '',
            )
        except PasswordResetError as exc:
            return Response({'detail': exc.message}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PasswordResetConfirmSerializer(data=request.data, context={'user': user})
        serializer.is_valid(raise_exception=True)

        reset_password(user, serializer.validated_data['new_password'])

        response = Response({'detail': 'Your password has been reset. You can now sign in.'})
        # Every refresh token for this account was just blacklisted; clearing
        # the cookie keeps this browser from retrying a token it can't use.
        _clear_refresh_cookie(response)
        return response
