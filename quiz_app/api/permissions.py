from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """Allow access only to the owner of a quiz."""

    def has_object_permission(self, request, view, obj):
        """Check whether the current user owns the quiz."""
        return obj.user_id == request.user.id
