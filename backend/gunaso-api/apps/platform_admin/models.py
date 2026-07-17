from django.conf import settings
from django.db import models


class PlatformAuditLog(models.Model):
    """Append-only record of every superadmin action — the immutable trail
    that comes with god-mode dashboard power. Never updated or deleted
    (enforced in Django admin too), mirroring StatusUpdate/StaffInvite.

    `target_repr` snapshots a human-readable label for the target at the
    time of the action, so the log stays readable even if the target is
    later renamed or deleted.
    """

    ACTION_CHOICES = [
        ('organization_verified', 'Organization Verified'),
        ('organization_unverified', 'Organization Unverified'),
        ('organization_activated', 'Organization Activated'),
        ('organization_deactivated', 'Organization Deactivated'),
        ('user_blocked', 'User Blocked'),
        ('user_unblocked', 'User Unblocked'),
        ('user_promoted', 'User Promoted to Superadmin'),
        ('user_demoted', 'User Demoted from Superadmin'),
    ]

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='platform_admin_actions',
    )
    action = models.CharField(max_length=40, choices=ACTION_CHOICES)
    target_type = models.CharField(max_length=50)
    target_id = models.PositiveIntegerField()
    target_repr = models.CharField(max_length=255)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'platform audit log'

    def __str__(self):
        return f'{self.get_action_display()}: {self.target_repr}'
