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


class ArticlePermissions(BasePermission):
    """
    Ensures users have correct access.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        # Only journalists can create
        if request.method == "POST":
            return user.role == "journalist"

        # Editors and journalists can modify
        if request.method in ["PUT", "PATCH", "DELETE"]:
            return user.role in ["journalist", "editor"]

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user

        if request.method in SAFE_METHODS:
            return True

        if user.role == "reader":
            return False

        if user.role == "journalist":
            allowed = obj.author_id == user.id
            return allowed

        if user.role == "editor":
            return (obj.publication and obj.publication in
                    user.edited_publications.all())

        return False
