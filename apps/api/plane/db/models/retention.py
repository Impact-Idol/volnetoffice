"""
HIPAA-Compliant Data Retention Models

This module provides data retention policy management with support for:
- Configurable retention periods (max 7 years per HIPAA)
- Legal hold exemptions for litigation
- Archive-before-delete workflows
- Audit trail of all retention actions
"""

import uuid

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

from ..mixins import TimeAuditModel


class RetentionPolicy(TimeAuditModel):
    """
    Data retention policy configuration.

    HIPAA requires retention of medical records for a minimum period
    (varies by state, typically 6-10 years). This model enforces a
    maximum of 7 years (2555 days) from date of entry.
    """

    MAX_RETENTION_DAYS = 2555  # 7 years

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Human-readable policy name"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of this retention policy"
    )

    # Retention configuration
    retention_days = models.IntegerField(
        default=2555,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(2555)
        ],
        help_text="Days from date of entry to retain. Max: 2555 (7 years)."
    )

    DATA_TYPE_CHOICES = [
        ('attachment', 'File Attachments'),
        ('issue', 'Issues'),
        ('issue_comment', 'Issue Comments'),
        ('audit_log', 'Audit Logs'),
        ('user', 'User Data'),
        ('project', 'Projects'),
        ('page', 'Pages'),
        ('notification', 'Notifications'),
        ('session', 'Sessions'),
        ('api_log', 'API Activity Logs'),
    ]
    data_type = models.CharField(
        max_length=50,
        choices=DATA_TYPE_CHOICES,
        help_text="Type of data this policy applies to"
    )

    # Processing options
    archive_before_delete = models.BooleanField(
        default=True,
        help_text="Archive data to cold storage before deletion"
    )
    only_archived = models.BooleanField(
        default=True,
        help_text="Only apply to already-archived/soft-deleted records"
    )
    require_approval = models.BooleanField(
        default=False,
        help_text="Require manual approval before deletion"
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this policy is actively enforced"
    )

    # Workspace scope (null = global policy)
    workspace_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Workspace this policy applies to (null = global)"
    )

    class Meta:
        db_table = 'retention_policies'
        verbose_name = 'Retention Policy'
        verbose_name_plural = 'Retention Policies'
        ordering = ['data_type', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['data_type', 'workspace_id'],
                name='unique_policy_per_data_type_workspace'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.data_type})"

    def get_cutoff_date(self):
        """Get the date before which data should be processed"""
        from datetime import timedelta
        return timezone.now() - timedelta(days=self.retention_days)


class RetentionExemption(TimeAuditModel):
    """
    Legal hold exemption - data under hold is NEVER deleted.

    This model tracks resources that are exempt from normal retention
    policies due to legal holds, litigation, or regulatory requirements.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Resource identification
    RESOURCE_TYPE_CHOICES = [
        ('attachment', 'File Attachment'),
        ('issue', 'Issue'),
        ('project', 'Project'),
        ('workspace', 'Workspace'),
        ('user', 'User'),
        ('page', 'Page'),
    ]
    resource_type = models.CharField(
        max_length=50,
        choices=RESOURCE_TYPE_CHOICES,
        help_text="Type of resource under hold"
    )
    resource_id = models.UUIDField(
        db_index=True,
        help_text="UUID of the resource under hold"
    )

    # Hold details
    reason = models.TextField(
        help_text="Reason for the legal hold"
    )
    legal_case_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Associated legal case number"
    )
    requesting_party = models.CharField(
        max_length=255,
        blank=True,
        help_text="Party who requested the hold"
    )

    # Duration
    hold_start = models.DateTimeField(
        auto_now_add=True,
        help_text="When the hold was placed"
    )
    hold_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the hold expires (null = indefinite)"
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether the hold is currently active"
    )
    released_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the hold was released"
    )
    released_by_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="User who released the hold"
    )
    release_reason = models.TextField(
        blank=True,
        help_text="Reason for releasing the hold"
    )

    # Audit
    created_by_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="User who created the hold"
    )

    class Meta:
        db_table = 'retention_exemptions'
        verbose_name = 'Retention Exemption'
        verbose_name_plural = 'Retention Exemptions'
        ordering = ['-hold_start']
        indexes = [
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['is_active', 'hold_until']),
        ]

    def __str__(self):
        status = "Active" if self.is_active else "Released"
        return f"{status} hold on {self.resource_type} {self.resource_id}"

    def is_currently_active(self):
        """Check if the hold is currently in effect"""
        if not self.is_active:
            return False
        if self.hold_until and self.hold_until < timezone.now():
            return False
        return True

    def release(self, user_id, reason=""):
        """Release the hold"""
        self.is_active = False
        self.released_at = timezone.now()
        self.released_by_id = user_id
        self.release_reason = reason
        self.save()


class RetentionJobRun(TimeAuditModel):
    """
    Record of retention job executions.

    Tracks each run of the retention enforcement job for audit purposes.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Job details
    policy = models.ForeignKey(
        RetentionPolicy,
        on_delete=models.SET_NULL,
        null=True,
        related_name='job_runs',
        help_text="Policy that was enforced"
    )

    # Timing
    started_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the job started"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the job completed"
    )

    # Results
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='running',
        help_text="Current status of the job"
    )

    records_scanned = models.IntegerField(
        default=0,
        help_text="Number of records evaluated"
    )
    records_archived = models.IntegerField(
        default=0,
        help_text="Number of records archived"
    )
    records_deleted = models.IntegerField(
        default=0,
        help_text="Number of records deleted"
    )
    records_exempted = models.IntegerField(
        default=0,
        help_text="Number of records skipped due to legal holds"
    )

    # Error tracking
    error_message = models.TextField(
        blank=True,
        help_text="Error message if job failed"
    )
    error_details = models.JSONField(
        default=dict,
        help_text="Detailed error information"
    )

    class Meta:
        db_table = 'retention_job_runs'
        verbose_name = 'Retention Job Run'
        verbose_name_plural = 'Retention Job Runs'
        ordering = ['-started_at']

    def __str__(self):
        return f"Retention job {self.id} ({self.status})"

    def complete(self, status='completed', error_message=''):
        """Mark the job as complete"""
        self.status = status
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.save()


class RetentionArchive(TimeAuditModel):
    """
    Record of archived data before deletion.

    Stores metadata about archived records for compliance tracking.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Original record info
    resource_type = models.CharField(
        max_length=50,
        help_text="Type of resource archived"
    )
    resource_id = models.UUIDField(
        help_text="Original UUID of the archived resource"
    )

    # Archive details
    archived_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the record was archived"
    )
    archive_location = models.CharField(
        max_length=500,
        blank=True,
        help_text="S3 path or storage location of archived data"
    )
    archive_checksum = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA-256 checksum of archived data"
    )

    # Deletion tracking
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the original record was deleted"
    )

    # Job reference
    job_run = models.ForeignKey(
        RetentionJobRun,
        on_delete=models.SET_NULL,
        null=True,
        related_name='archives',
        help_text="Job run that created this archive"
    )

    # Metadata snapshot
    metadata_snapshot = models.JSONField(
        default=dict,
        help_text="Snapshot of key metadata at time of archival"
    )

    class Meta:
        db_table = 'retention_archives'
        verbose_name = 'Retention Archive'
        verbose_name_plural = 'Retention Archives'
        ordering = ['-archived_at']
        indexes = [
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['archived_at']),
        ]

    def __str__(self):
        return f"Archive of {self.resource_type} {self.resource_id}"
