from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsEditorOrJournalist(BasePermission):
    """
    To ensure user is an editor or journalist.
     """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in ["editor", "journalist"]
        )


class ReadOnly(BasePermission):
    """
    To enforce read only permission.
    """
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS
