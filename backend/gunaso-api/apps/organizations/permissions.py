from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

from .models import OrganizationStaff


class IsOrgAdmin(permissions.BasePermission):
    """Allow access only to users with user_type == 'org_admin'."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.user_type == 'org_admin'
        )


class IsOrgAdminOfOrg(permissions.BasePermission):
    """Allow access only to the org_admin who owns this organization (or platform staff)."""

    message = "Only this organization's admin can perform this action."

    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and (
            obj.admin_id == request.user.id or request.user.is_staff
        )

    def check(self, request, org):
        """Imperative form for views that resolve the organization themselves."""
        if not self.has_object_permission(request, None, org):
            raise PermissionDenied(self.message)


class HasOrgPrivilege(permissions.BasePermission):
    """
    Allow the organization's admin, platform staff, or an *active* staff
    member whose role grants a specific privilege.

    Denied (403) for anyone else — including an invited-but-not-yet-accepted
    staff member, a disabled (``is_active=False``) staff member, a staff
    member whose ``status`` is not ``'active'``, and an active staff member
    whose role simply doesn't include the required privilege.

    Parameterized by privilege key so one class can back many views:

        # Imperative form, for views that resolve the organization themselves
        # (mirrors IsOrgAdminOfOrg.check):
        HasOrgPrivilege('view_stats').check(request, org)

        # Declarative form, for use in `permission_classes`:
        permission_classes = [require_privilege('view_stats')]
    """

    message = "You do not have permission to perform this action for this organization."
    privilege = None

    def __init__(self, privilege=None):
        if privilege is not None:
            self.privilege = privilege

    def has_object_permission(self, request, view, obj):
        return self._is_allowed(request, obj)

    def check(self, request, org):
        """Imperative form for views that resolve the organization themselves."""
        if not self._is_allowed(request, org):
            raise PermissionDenied(self.message)

    def _is_allowed(self, request, org):
        user = getattr(request, 'user', None)
        if not (user and user.is_authenticated):
            return False
        if org.admin_id == user.id or user.is_staff:
            return True
        if not self.privilege:
            return False

        staff = (
            OrganizationStaff.objects.filter(
                organization=org, user=user, status='active', is_active=True,
            )
            .select_related('role')
            .first()
        )
        if staff is None or staff.role is None:
            return False
        # Checked in Python (not a JSONField `contains` ORM lookup) so this
        # behaves identically on the sqlite fallback and on PostgreSQL.
        return self.privilege in (staff.role.privileges or [])


def require_privilege(privilege):
    """Factory returning a `HasOrgPrivilege` subclass bound to `privilege`.

    DRF instantiates each entry in `permission_classes` with no constructor
    arguments, so a plain `HasOrgPrivilege('x')` instance can't be placed
    there directly — this factory produces a zero-arg-constructible class
    instead, for views where DRF (rather than the view body) resolves the
    object via `has_object_permission`.
    """

    class _BoundHasOrgPrivilege(HasOrgPrivilege):
        def __init__(self):
            super().__init__(privilege)

    _BoundHasOrgPrivilege.__name__ = f'HasOrgPrivilege_{privilege}'
    return _BoundHasOrgPrivilege
