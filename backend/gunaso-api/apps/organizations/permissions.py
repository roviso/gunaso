from rest_framework import permissions


class IsOrgAdmin(permissions.BasePermission):
    """Allow access only to users with user_type == 'org_admin'."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.user_type == 'org_admin'
        )


class IsOrgAdminOfOrg(permissions.BasePermission):
    """Allow access only to the org_admin who owns this organization."""

    def has_object_permission(self, request, view, obj):
        return (
            request.user
            and request.user.is_authenticated
            and obj.admin == request.user
        )
