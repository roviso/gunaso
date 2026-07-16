"""Fixed catalog of privileges an org admin can grant to a custom StaffRole.

Privileges are looked up by `key` (the value stored in `StaffRole.privileges`,
a list of strings). `label` and `group` exist purely for presenting the
catalog to org admins when building a role (e.g. in a role-editor UI) and
carry no runtime meaning on their own.
"""

STAFF_PRIVILEGES = [
    {
        'key': 'view_submissions',
        'label': 'View submissions',
        'group': 'submissions',
    },
    {
        'key': 'manage_submissions',
        'label': 'Manage submissions (status, notes)',
        'group': 'submissions',
    },
    {
        'key': 'assign_submissions',
        'label': 'Assign submissions to staff',
        'group': 'submissions',
    },
    {
        'key': 'view_stats',
        'label': 'View organization statistics',
        'group': 'reporting',
    },
    {
        'key': 'view_staff',
        'label': 'View staff members',
        'group': 'staff',
    },
    {
        'key': 'manage_staff',
        'label': 'Add, edit, and remove staff members',
        'group': 'staff',
    },
    {
        'key': 'manage_roles',
        'label': 'Create and edit staff roles',
        'group': 'staff',
    },
    {
        'key': 'manage_org_profile',
        'label': 'Edit organization profile',
        'group': 'organization',
    },
]

STAFF_PRIVILEGE_KEYS = {privilege['key'] for privilege in STAFF_PRIVILEGES}
