"""
HIPAA-Compliant Immutable Audit Log

This module provides an immutable audit logging system that meets HIPAA requirements
for tracking access to Protected Health Information (PHI).

Key features:
- Immutable records (cannot be modified or deleted)
- Cryptographic checksum for integrity verification
- Hashed user identifiers for privacy
- PHI access tracking flag
- IP address and user agent logging
"""

import uuid
import hashlib
import json

from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError


class AuditLogManager(models.Manager):
    """Custom manager that prevents bulk deletion"""

    def bulk_delete(self, *args, **kwargs):
        raise ValidationError("Audit logs cannot be bulk deleted")


class AuditLog(models.Model):
    """
    Immutable HIPAA audit log - records cannot be modified or deleted.

    This model provides a complete audit trail of all actions in the system,
    with special tracking for PHI access events.
    """

    # Primary key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Event information
    action = models.CharField(
        max_length=100,
        db_index=True,
        help_text="The action performed (e.g., VIEW_ISSUE, UPDATE_USER)"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the action occurred"
    )

    # Actor information
    user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID of the user who performed the action"
    )
    user_email_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="SHA-256 hash of user email for privacy-preserving identification"
    )
    actor_type = models.CharField(
        max_length=50,
        default='user',
        help_text="Type of actor: user, system, api_token, webhook"
    )

    # Resource information
    workspace_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID of the workspace context"
    )
    workspace_slug = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Slug of the workspace for human-readable reference"
    )
    project_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID of the project context"
    )
    resource_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        help_text="Type of resource accessed (e.g., issue, user, attachment)"
    )
    resource_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID of the specific resource"
    )

    # Request context
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the request"
    )
    user_agent = models.TextField(
        null=True,
        blank=True,
        help_text="User agent string from the request"
    )
    request_id = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="Unique request identifier for correlation"
    )
    session_id = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="Session identifier"
    )

    # Additional data
    data = models.JSONField(
        default=dict,
        help_text="Additional structured data about the action"
    )
    changes = models.JSONField(
        default=dict,
        null=True,
        blank=True,
        help_text="Before/after values for update operations"
    )

    # HIPAA-specific fields
    phi_accessed = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether Protected Health Information was accessed"
    )
    phi_fields = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
        help_text="List of PHI fields that were accessed"
    )

    # Integrity verification
    checksum = models.CharField(
        max_length=64,
        help_text="SHA-256 checksum for integrity verification"
    )

    # Status
    severity = models.CharField(
        max_length=20,
        default='info',
        choices=[
            ('debug', 'Debug'),
            ('info', 'Info'),
            ('warning', 'Warning'),
            ('error', 'Error'),
            ('critical', 'Critical'),
        ],
        help_text="Severity level of the audit event"
    )

    objects = AuditLogManager()

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['user_id', 'timestamp']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['phi_accessed', 'timestamp']),
            models.Index(fields=['workspace_id', 'project_id', 'timestamp']),
        ]
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        return f"{self.action} by {self.user_id} at {self.timestamp}"

    def _compute_checksum(self):
        """Compute SHA-256 checksum of audit log data"""
        log_data = {
            'action': self.action,
            'user_id': str(self.user_id) if self.user_id else None,
            'user_email_hash': self.user_email_hash,
            'workspace_id': str(self.workspace_id) if self.workspace_id else None,
            'project_id': str(self.project_id) if self.project_id else None,
            'resource_type': self.resource_type,
            'resource_id': str(self.resource_id) if self.resource_id else None,
            'ip_address': self.ip_address,
            'data': self.data,
            'phi_accessed': self.phi_accessed,
        }
        return hashlib.sha256(
            json.dumps(log_data, sort_keys=True, default=str).encode()
        ).hexdigest()

    def save(self, *args, **kwargs):
        """Override save to enforce immutability and compute checksum"""
        # Prevent modification of existing records
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise ValidationError('Audit logs cannot be modified once created')

        # Compute checksum before saving
        if not self.checksum:
            self.checksum = self._compute_checksum()

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Override delete to prevent deletion"""
        raise ValidationError('Audit logs cannot be deleted')

    def verify_integrity(self):
        """Verify the integrity of the audit log entry"""
        computed = self._compute_checksum()
        return computed == self.checksum


class PHIAccessLog(models.Model):
    """
    Specialized log for PHI access events.

    This provides a dedicated view of all PHI access for compliance reporting.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Reference to main audit log
    audit_log = models.ForeignKey(
        AuditLog,
        on_delete=models.PROTECT,
        related_name='phi_access_logs'
    )

    # PHI-specific tracking
    phi_category = models.CharField(
        max_length=50,
        choices=[
            ('demographics', 'Demographics'),
            ('contact', 'Contact Information'),
            ('health', 'Health Information'),
            ('financial', 'Financial Information'),
            ('employment', 'Employment Information'),
            ('case_notes', 'Case Notes'),
            ('attachments', 'Attachments'),
        ],
        help_text="Category of PHI accessed"
    )
    access_reason = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Documented reason for accessing PHI"
    )
    data_subject_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID of the person whose PHI was accessed"
    )

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'phi_access_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['phi_category', 'timestamp']),
            models.Index(fields=['data_subject_id', 'timestamp']),
        ]
        verbose_name = 'PHI Access Log'
        verbose_name_plural = 'PHI Access Logs'

    def save(self, *args, **kwargs):
        """Prevent modification of existing records"""
        if self.pk and PHIAccessLog.objects.filter(pk=self.pk).exists():
            raise ValidationError('PHI access logs cannot be modified once created')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion"""
        raise ValidationError('PHI access logs cannot be deleted')
