from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken


def set_jwt_cookies(response, refresh):
    """Set access and refresh tokens as HTTP-only cookies."""
    set_access_token_cookie(response, refresh.access_token)
    response.set_cookie(
        key='refresh_token',
        value=str(refresh),
        httponly=True,
    )


def create_login_response(user):
    """Create the response for a successful login."""

    data = {
        'detail': 'Login successful!',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
        },
    }
    return Response(data, status=status.HTTP_200_OK)


def delete_jwt_cookies(response):
    """Delete access and refresh token cookies."""
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')


def set_access_token_cookie(response, access_token):
    """Set the access token as an HTTP-only cookie."""

    response.set_cookie(
        key='access_token',
        value=str(access_token),
        httponly=True,
    )


def get_valid_refresh_token(refresh_token):
    """Validate and return a refresh token."""

    refresh = RefreshToken(refresh_token)
    return refresh


def create_refresh_error_response(detail):
    """Create an unauthorized response for a refresh error."""
    return Response(
        {'detail': detail},
        status=status.HTTP_401_UNAUTHORIZED,
    )


def create_refresh_response(refresh):
    """Create a response with a refreshed access token."""
    access_token = refresh.access_token
    response = Response(
        {'detail': 'Token refreshed successfully!'},
        status=status.HTTP_200_OK,
    )
    set_access_token_cookie(response, access_token)
    return response
