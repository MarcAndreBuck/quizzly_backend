from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RegistrationSerializer, LoginSerializer
from .utils import set_jwt_cookies, create_login_response, delete_jwt_cookies
from .authentication import CookieJWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken


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

        response = Response(
            {'detail': 'Logout successful!'},
            status=status.HTTP_200_OK,
        )
        delete_jwt_cookies(response)
        return response
