from django.db import models


class RevokedAccessToken(models.Model):
    """Record an access token revoked during logout."""

    jti = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return self.jti
