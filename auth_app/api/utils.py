from datetime import datetime, timezone

from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from auth_app.models import RevokedAccessToken


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
        'detail': 'Login successfully!',
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
        {'detail': 'Token refreshed'},
        status=status.HTTP_200_OK,
    )
    set_access_token_cookie(response, access_token)
    return response


def revoke_access_token(token):
    """Record an access token as revoked until it expires."""
    RevokedAccessToken.objects.get_or_create(
        jti=token['jti'],
        defaults={
            'expires_at': datetime.fromtimestamp(token['exp'], tz=timezone.utc)
        },
    )


def create_logout_response():
    """Create the logout response and clear both JWT cookies."""
    response = Response(
        {
            'detail': (
                'Log-Out successfully! All Tokens will be deleted. '
                'Refresh token is now invalid.'
            )
        },
        status=status.HTTP_200_OK,
    )
    delete_jwt_cookies(response)
    return response
