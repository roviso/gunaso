from django.db import models
from apps.accounts.models import User
from apps.organizations.models import Organization


class Category(models.Model):
    name = models.CharField(max_length=100)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE,
        null=True, blank=True, related_name='categories',
    )

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']

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
        ('escalated', 'Escalated'),
        ('closed', 'Closed'),
    ]
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

    reference_number = models.CharField(max_length=20, unique=True)
    citizen = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='submissions',
    )
    citizen_name = models.CharField(max_length=200)
    citizen_email = models.EmailField()
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
    attachment = models.FileField(upload_to='attachments/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    is_anonymous = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.reference_number}] {self.title}'


class StatusUpdate(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='updates')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    old_status = models.CharField(max_length=50)
    new_status = models.CharField(max_length=50)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.submission.reference_number}: {self.old_status} → {self.new_status}'
