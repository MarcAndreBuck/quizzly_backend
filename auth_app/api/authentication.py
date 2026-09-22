from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticate users with a JWT stored in an HTTP-only cookie."""

    def authenticate(self, request):
        """Authenticate a user using the access token cookie."""
        raw_token = request.COOKIES.get('access_token')
        if raw_token is None:
            return None
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
