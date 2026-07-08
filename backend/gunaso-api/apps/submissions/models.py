from django.db import models

from apps.accounts.models import User
from apps.organizations.models import Organization


class InvalidStatusTransitionError(Exception):
    """Raised when a submission status change is not an allowed transition."""


class Category(models.Model):
    name = models.CharField(max_length=100)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE,
        null=True, blank=True, related_name='categories',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['name', 'organization'], name='unique_category_per_org'),
        ]

    def __str__(self):
        if self.organization:
            return f'{self.name} ({self.organization.name})'
        return f'{self.name} (Global)'


class Submission(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('acknowledged', 'Acknowledged'),
        ('in_review', 'In Review'),
        ('resolved', 'Resolved'),
        ('rejected', 'Rejected'),
        ('escalated', 'Escalated'),
        ('closed', 'Closed'),
    ]

    # Allowed status transitions. Terminal state: closed.
    VALID_TRANSITIONS = {
        'submitted': {'acknowledged', 'in_review', 'rejected', 'escalated'},
        'acknowledged': {'in_review', 'rejected', 'escalated'},
        'in_review': {'resolved', 'rejected', 'escalated'},
        'escalated': {'in_review', 'resolved', 'rejected'},
        'resolved': {'closed'},
        'rejected': {'closed'},
        'closed': set(),
    }

    TYPE_CHOICES = [
        ('complaint', 'Complaint'),
        ('feedback', 'Feedback'),
        ('suggestion', 'Suggestion'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    reference_number = models.CharField(max_length=20, unique=True, db_index=True)
    citizen = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='submissions',
    )
    citizen_name = models.CharField(max_length=200, blank=True)
    citizen_email = models.EmailField(blank=True)
    citizen_phone = models.CharField(max_length=20, blank=True)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='submissions',
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
    )
    submission_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='complaint')
    title = models.CharField(max_length=255)
    description = models.TextField()
    attachment = models.FileField(upload_to='attachments/%Y/%m/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    is_anonymous = models.BooleanField(default=False)
    assigned_to = models.ForeignKey(
        'organizations.OrganizationStaff',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_submissions',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'submissions'
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['citizen', '-created_at']),
        ]

    def __str__(self):
        return f'[{self.reference_number}] {self.title}'

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in self.VALID_TRANSITIONS.get(self.status, set())


class StatusUpdate(models.Model):
    """Append-only audit log of status changes. Records are never updated or deleted."""

    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='updates')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    old_status = models.CharField(max_length=50)
    new_status = models.CharField(max_length=50)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name_plural = 'status updates'

    def __str__(self):
        return f'{self.submission.reference_number}: {self.old_status} → {self.new_status}'
