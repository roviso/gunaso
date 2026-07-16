import django.db.models.deletion
from django.db import migrations, models

# Snapshot of the default privilege sets for the legacy fixed roles, frozen
# here (rather than imported from apps.organizations.privileges) so this
# migration keeps producing the same result regardless of future catalog
# changes. Matches the mapping agreed for this data backfill:
#   manager/supervisor -> manage_submissions, assign_submissions, view_stats, view_staff
#   agent               -> view_submissions, manage_submissions
#   viewer              -> view_submissions
DEFAULT_ROLE_PRIVILEGES = {
    'manager': ['manage_submissions', 'assign_submissions', 'view_stats', 'view_staff'],
    'supervisor': ['manage_submissions', 'assign_submissions', 'view_stats', 'view_staff'],
    'agent': ['view_submissions', 'manage_submissions'],
    'viewer': ['view_submissions'],
}

LEGACY_ROLE_LABELS = {
    'manager': 'Manager',
    'agent': 'Support Agent',
    'supervisor': 'Supervisor',
    'viewer': 'Viewer',
}


def populate_staff_roles(apps, schema_editor):
    OrganizationStaff = apps.get_model('organizations', 'OrganizationStaff')
    StaffRole = apps.get_model('organizations', 'StaffRole')

    role_cache = {}  # (organization_id, legacy_role) -> StaffRole pk

    for staff in OrganizationStaff.objects.all().only('id', 'organization_id', 'legacy_role'):
        legacy_role = staff.legacy_role or 'agent'
        cache_key = (staff.organization_id, legacy_role)
        role_id = role_cache.get(cache_key)
        if role_id is None:
            privileges = DEFAULT_ROLE_PRIVILEGES.get(legacy_role, ['view_submissions'])
            name = LEGACY_ROLE_LABELS.get(legacy_role, legacy_role.title())
            role, _ = StaffRole.objects.get_or_create(
                organization_id=staff.organization_id,
                name=name,
                defaults={'privileges': privileges},
            )
            role_id = role.pk
            role_cache[cache_key] = role_id
        staff.role_id = role_id
        staff.save(update_fields=['role'])


def noop_reverse(apps, schema_editor):
    """No meaningful reverse: legacy_role values are gone once forward has run."""


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0004_staffrole_staffinvite'),
    ]

    operations = [
        migrations.RunPython(populate_staff_roles, noop_reverse),
        migrations.RemoveField(
            model_name='organizationstaff',
            name='legacy_role',
        ),
        migrations.AlterField(
            model_name='organizationstaff',
            name='role',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='staff_members',
                to='organizations.staffrole',
            ),
        ),
    ]
