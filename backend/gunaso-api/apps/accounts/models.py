from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    USER_TYPE_CHOICES = [
        ('citizen', 'Citizen'),
        ('org_admin', 'Org Admin'),
        ('stakeholder', 'Stakeholder'),
    ]
    # Email is the login identifier — must be unique.
    email = models.EmailField(unique=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='citizen')
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    # True for every path where the user has proven inbox ownership (self
    # registration, org registration, accepting an emailed staff invite).
    # False only for accounts an org admin creates directly with a chosen
    # username/password — the email on those is admin-typed and unproven
    # until the holder verifies it themselves (apps/accounts/views.py).
    email_verified = models.BooleanField(default=True)
    # Forces a password change on next login. Set True only when an org admin
    # assigns the initial password (apps/organizations/services.py) so a
    # temporary, admin-known credential can't remain valid indefinitely.
    must_change_password = models.BooleanField(default=False)

    class Meta:
        ordering = ['username']

    def __str__(self):
        return f'{self.username} ({self.get_user_type_display()})'
