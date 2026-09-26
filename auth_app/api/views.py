from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .authentication import CookieJWTAuthentication
from .serializers import LoginSerializer, RegistrationSerializer
from .utils import (
    create_login_response,
    create_logout_response,
    create_refresh_error_response,
    create_refresh_response,
    get_valid_refresh_token,
    revoke_access_token,
    set_jwt_cookies,
)


class RegistrationView(APIView):
    """View for user registration."""
    permission_classes = [AllowAny]

    def post(self, request):
        """Register a new user."""
        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {'detail': 'User created successfully!'},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """View for user login."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Authenticate a user."""
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            response = create_login_response(user)
            set_jwt_cookies(response, refresh)
            return response

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """View for user logout."""

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Log out the authenticated user."""
        refresh_token = request.COOKIES.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()

        revoke_access_token(request.auth)

        return create_logout_response()


class TokenRefreshView(APIView):
    """View for refreshing the access token."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """Refresh the access token using the refresh token cookie."""
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return create_refresh_error_response('Refresh token not provided.')
        try:
            refresh = get_valid_refresh_token(refresh_token)
        except TokenError:
            return create_refresh_error_response(
                'Invalid or expired refresh token.'
            )
        return create_refresh_response(refresh)
