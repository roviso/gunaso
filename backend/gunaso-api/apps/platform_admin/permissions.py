from rest_framework import permissions


class IsSuperAdmin(permissions.BasePermission):
    """Allow access only to platform superadmins (`User.is_superuser`).

    Deliberately distinct from `is_staff`, which already grants the
    pre-existing "platform staff" bypasses used throughout the app
    (anonymity reveal in submissions, IsOrgAdminOfOrg, HasOrgPrivilege — see
    apps/organizations/permissions.py). `is_superuser` gates this dashboard
    specifically: verifying/blocking/promoting. Promoting a user sets both
    flags (services.promote_to_superadmin) so a superadmin also inherits
    every existing is_staff bypass elsewhere in the app.
    """

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.is_superuser
        )
