from rest_framework.response import Response
from rest_framework import status


def set_jwt_cookies(response, refresh):
    """Set access and refresh tokens as HTTP-only cookies."""
    response.set_cookie(
        key='access_token',
        value=str(refresh.access_token),
        httponly=True,
    )
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
