from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsEditor(BasePermission):
    """
    Allow access only to users who are editors.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "editor"


class IsJournalist(BasePermission):
    """
    Allow access only to users who are journalists.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and request.user.role == "journalist"
            )


class ReadOnly(BasePermission):
    """
    Allow read-only access for readers.
    """
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS
