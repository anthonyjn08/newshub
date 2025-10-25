from rest_framework.permissions import BasePermission


class IsReader(BasePermission):
    """Only allow readers to subscribe."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "reader"
