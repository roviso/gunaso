from django.db import models

from apps.accounts.models import User


class Organization(models.Model):

    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    category = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='org_logos/', null=True, blank=True)
    website = models.URLField(blank=True)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='managed_organizations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'organizations'

    def __str__(self):
        return self.name


class Stakeholder(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='stakeholders')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=100)
    receives_all = models.BooleanField(default=True)

    class Meta:
        unique_together = ('organization', 'user')
        ordering = ['organization', 'user']
        verbose_name_plural = 'stakeholders'

    def __str__(self):
        return f'{self.user.username} @ {self.organization.name} ({self.role})'


class StaffRole(models.Model):
    """A per-organization, admin-defined role carrying a chosen set of privileges.

    `privileges` stores a list of keys drawn from `privileges.STAFF_PRIVILEGE_KEYS`.
    Validation of that list lives in services/serializers, not here — models stay thin.
    """

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='staff_roles')
    name = models.CharField(max_length=100)
    privileges = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('organization', 'name')
        ordering = ['organization', 'name']
        verbose_name_plural = 'staff roles'

    def __str__(self):
        return f'{self.name} @ {self.organization.name}'


class OrganizationStaff(models.Model):
    STATUS_CHOICES = [
        ('invited', 'Invited'),
        ('active', 'Active'),
        ('disabled', 'Disabled'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='staff_members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='staff_roles')
    role = models.ForeignKey(StaffRole, on_delete=models.PROTECT, related_name='staff_members')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='invited')
    is_active = models.BooleanField(default=True)
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='staff_assignments'
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('organization', 'user')
        ordering = ['organization', 'role', 'user']
        verbose_name_plural = 'organization staff'

    def __str__(self):
        return f'{self.user.username} @ {self.organization.name} [{self.role.name}]'


class StaffInvite(models.Model):
    """Single-use, expiring invite for a staff member who has no account yet.

    Append-only, like `StatusUpdate`: only the hash of the invite token is ever
    persisted, and rows are never edited or deleted once created (see admin.py).
    """

    staff = models.OneToOneField(OrganizationStaff, on_delete=models.CASCADE, related_name='invite')
    token_hash = models.CharField(max_length=128, unique=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='staff_invites_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'staff invites'

    def __str__(self):
        return f'Invite for {self.staff} (expires {self.expires_at:%Y-%m-%d})'
