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

    class Meta:
        ordering = ['username']

    def __str__(self):
        return f'{self.username} ({self.get_user_type_display()})'
