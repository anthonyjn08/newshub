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


class PublicationPermissions(BasePermission):
    """
    Custom permissions for Publication API.
    """
    def has_permission(self, request, view):
        user = request.user

        # Must be authenticated
        if not user.is_authenticated:
            return False

        # Safe methods (GET, HEAD, OPTIONS): allowed for all roles
        if request.method in SAFE_METHODS:
            return True

        # Only editors can modify or create
        return user.role == "editor"

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Safe methods are always allowed
        if request.method in SAFE_METHODS:
            return True

        # Editors can modify only their own publications
        return user.role == "editor" and user in obj.editors.all()


class EditorOnlyPermission(BasePermission):
    """
    Grants access only to editors for unsafe methods (POST, PATCH, DELETE),
    but allows everyone to view (GET, HEAD, OPTIONS).
    """

    def has_permission(self, request, view):
        # Allow read-only access to anyone authenticated
        if request.method in SAFE_METHODS:
            return True

        # Only editors can perform write actions
        return (
            request.user.is_authenticated
            and getattr(request.user, "role", None) == "editor"
        )

    def has_object_permission(self, request, view, obj):
        # Editors can only modify their own publications
        if request.method in SAFE_METHODS:
            return True

        return obj.editors.filter(id=request.user.id).exists()
