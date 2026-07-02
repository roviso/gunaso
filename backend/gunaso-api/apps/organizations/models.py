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
    is_verified = models.BooleanField(default=False)
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='managed_organizations')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Stakeholder(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='stakeholders')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=100)
    receives_all = models.BooleanField(default=True)

    class Meta:
        unique_together = ('organization', 'user')

    def __str__(self):
        return f'{self.user.username} @ {self.organization.name} ({self.role})'
