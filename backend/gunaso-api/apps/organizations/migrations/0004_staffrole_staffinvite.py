import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0003_organizationstaff'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StaffRole',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('name', models.CharField(max_length=100)),
                ('privileges', models.JSONField(default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'organization',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='staff_roles',
                        to='organizations.organization',
                    ),
                ),
            ],
            options={
                'verbose_name_plural': 'staff roles',
                'ordering': ['organization', 'name'],
                'unique_together': {('organization', 'name')},
            },
        ),
        # Rename the legacy fixed-choice CharField out of the way so the new
        # FK can take the `role` name. Populated + dropped in the follow-up
        # data migration.
        migrations.RenameField(
            model_name='organizationstaff',
            old_name='role',
            new_name='legacy_role',
        ),
        migrations.AddField(
            model_name='organizationstaff',
            name='status',
            field=models.CharField(
                choices=[
                    ('invited', 'Invited'),
                    ('active', 'Active'),
                    ('disabled', 'Disabled'),
                ],
                default='invited',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='organizationstaff',
            name='role',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='staff_members',
                to='organizations.staffrole',
            ),
        ),
        migrations.CreateModel(
            name='StaffInvite',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('token_hash', models.CharField(max_length=128, unique=True)),
                ('expires_at', models.DateTimeField()),
                ('accepted_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                (
                    'created_by',
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='staff_invites_created',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'staff',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='invite',
                        to='organizations.organizationstaff',
                    ),
                ),
            ],
            options={
                'verbose_name_plural': 'staff invites',
                'ordering': ['-created_at'],
            },
        ),
    ]
