from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RegistrationSerializer, LoginSerializer
from .utils import set_jwt_cookies
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
            response = Response(
                {
                    'detail': 'Login successful!',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                    },
                },
                status=status.HTTP_200_OK,
            )
            set_jwt_cookies(response, refresh)
            return response

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
