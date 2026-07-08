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


class OrganizationStaff(models.Model):
    ROLE_CHOICES = [
        ('manager', 'Manager'),
        ('agent', 'Support Agent'),
        ('supervisor', 'Supervisor'),
        ('viewer', 'Viewer'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='staff_members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='staff_roles')
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='agent')
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
        return f'{self.user.username} @ {self.organization.name} [{self.get_role_display()}]'
