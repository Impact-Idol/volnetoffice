# Type imports
from typing import Any

# Python imports
import base64
import os

# Django imports
from django.db import models
from django.utils import timezone
from django.conf import settings

# Third party imports
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Module imports
from plane.bgtasks.deletion_task import soft_delete_related_objects


# =============================================================================
# HIPAA-COMPLIANT ENCRYPTED FIELDS
# =============================================================================

def get_encryption_key():
    """Get or generate encryption key from settings"""
    key = getattr(settings, 'ENCRYPTION_KEY', None)
    if key:
        # If key is a string, encode it
        if isinstance(key, str):
            # Ensure it's a valid Fernet key (32 url-safe base64-encoded bytes)
            return key.encode() if len(key) == 44 else Fernet.generate_key()
        return key
    # Generate a key for development (should be set in production)
    return Fernet.generate_key()


class EncryptedTextField(models.TextField):
    """
    AES-256 encrypted text field for HIPAA-compliant PHI storage.

    Uses Fernet symmetric encryption (AES-128-CBC with HMAC).
    Data is base64 encoded for storage in text fields.
    """

    description = "An AES-256 encrypted text field"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _get_fernet(self):
        """Lazy load Fernet to avoid issues during migrations"""
        if not hasattr(self, '_fernet'):
            self._fernet = Fernet(get_encryption_key())
        return self._fernet

    def get_prep_value(self, value):
        """Encrypt value before saving to database"""
        if value is None:
            return value
        if isinstance(value, str):
            value = value.encode('utf-8')
        encrypted = self._get_fernet().encrypt(value)
        return base64.b64encode(encrypted).decode('utf-8')

    def from_db_value(self, value, expression, connection):
        """Decrypt value when reading from database"""
        if value is None:
            return value
        try:
            encrypted = base64.b64decode(value.encode('utf-8'))
            decrypted = self._get_fernet().decrypt(encrypted)
            return decrypted.decode('utf-8')
        except Exception:
            # Return raw value if decryption fails (for legacy data)
            return value

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        return name, path, args, kwargs


class EncryptedCharField(models.CharField):
    """
    AES-256 encrypted char field for HIPAA-compliant PHI storage.

    Note: max_length should account for encryption overhead (~1.5x original).
    """

    description = "An AES-256 encrypted char field"

    def __init__(self, *args, **kwargs):
        # Increase max_length to account for encryption overhead
        if 'max_length' in kwargs:
            kwargs['max_length'] = max(kwargs['max_length'] * 2, 255)
        super().__init__(*args, **kwargs)

    def _get_fernet(self):
        """Lazy load Fernet to avoid issues during migrations"""
        if not hasattr(self, '_fernet'):
            self._fernet = Fernet(get_encryption_key())
        return self._fernet

    def get_prep_value(self, value):
        """Encrypt value before saving to database"""
        if value is None:
            return value
        if isinstance(value, str):
            value = value.encode('utf-8')
        encrypted = self._get_fernet().encrypt(value)
        return base64.b64encode(encrypted).decode('utf-8')

    def from_db_value(self, value, expression, connection):
        """Decrypt value when reading from database"""
        if value is None:
            return value
        try:
            encrypted = base64.b64decode(value.encode('utf-8'))
            decrypted = self._get_fernet().decrypt(encrypted)
            return decrypted.decode('utf-8')
        except Exception:
            # Return raw value if decryption fails (for legacy data)
            return value

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        return name, path, args, kwargs


class EncryptedEmailField(EncryptedCharField):
    """
    AES-256 encrypted email field for HIPAA-compliant PHI storage.
    """

    description = "An AES-256 encrypted email field"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 254)
        super().__init__(*args, **kwargs)


class TimeAuditModel(models.Model):
    """To path when the record was created and last modified"""

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last Modified At")

    class Meta:
        abstract = True


class UserAuditModel(models.Model):
    """To path when the record was created and last modified"""

    created_by = models.ForeignKey(
        "db.User",
        on_delete=models.SET_NULL,
        related_name="%(class)s_created_by",
        verbose_name="Created By",
        null=True,
    )
    updated_by = models.ForeignKey(
        "db.User",
        on_delete=models.SET_NULL,
        related_name="%(class)s_updated_by",
        verbose_name="Last Modified By",
        null=True,
    )

    class Meta:
        abstract = True


class SoftDeletionQuerySet(models.QuerySet):
    def delete(self, soft=True):
        if soft:
            return self.update(deleted_at=timezone.now())
        else:
            return super().delete()


class SoftDeletionManager(models.Manager):
    def get_queryset(self):
        return SoftDeletionQuerySet(self.model, using=self._db).filter(deleted_at__isnull=True)


class SoftDeleteModel(models.Model):
    """To soft delete records"""

    deleted_at = models.DateTimeField(verbose_name="Deleted At", null=True, blank=True)

    objects = SoftDeletionManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, soft=True, *args, **kwargs):
        if soft:
            # Soft delete the current instance
            self.deleted_at = timezone.now()
            self.save(using=using)

            soft_delete_related_objects.delay(self._meta.app_label, self._meta.model_name, self.pk, using=using)

        else:
            # Perform hard delete if soft deletion is not enabled
            return super().delete(using=using, *args, **kwargs)


class AuditModel(TimeAuditModel, UserAuditModel, SoftDeleteModel):
    """To path when the record was created and last modified"""

    class Meta:
        abstract = True


class ChangeTrackerMixin:
    """
    A mixin to track changes in model fields between initialization and save.

    This mixin captures the initial state of model fields when the instance is
    created and provides utilities to detect which fields have changed.

    Usage:
        To track specific fields, define a TRACKED_FIELDS list on your model:

        class MyModel(ChangeTrackerMixin, models.Model):
            TRACKED_FIELDS = ['field1', 'field2', 'field3']
            field1 = models.CharField(max_length=100)
            field2 = models.IntegerField()
            field3 = models.BooleanField()

        If TRACKED_FIELDS is not defined, all non-deferred fields will be tracked.

    Properties:
        changed_fields: A list of field names that have changed since initialization.
        old_values: A dictionary mapping field names to their original values.

    Methods:
        has_changed(field_name): Check if a specific field has changed.

    Notes:
        - Deferred fields (from .defer() or .only()) are automatically excluded
          from tracking to avoid triggering database queries.
        - Field values are captured in __init__, so changes are tracked relative
          to the initial state when the instance was loaded from the database.
    """

    _original_values: dict[str, Any]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._original_values = {}
        self._track_fields()

    def _track_fields(self) -> None:
        """
        Capture the initial values of fields to track.

        This method stores the current values of fields that should be tracked.
        If TRACKED_FIELDS is defined on the model, only those fields are tracked.
        Otherwise, all non-deferred fields are tracked. Deferred fields are
        automatically excluded to prevent unnecessary database queries.
        """
        deferred_fields = self.get_deferred_fields()
        tracked_fields = getattr(self, "TRACKED_FIELDS", None)
        if tracked_fields:
            for field in tracked_fields:
                if field not in deferred_fields:
                    self._original_values[field] = getattr(self, field)
        else:
            for field in self._meta.fields:
                if field.attname not in deferred_fields:
                    self._original_values[field.attname] = getattr(self, field.attname)

    def has_changed(self, field_name: str) -> bool:
        """
        Check if a specific field has changed since initialization.

        Args:
            field_name (str): The name of the field to check.

        Returns:
            bool: True if the field has changed, False otherwise. Returns False
                  if the field was not being tracked or is deferred.
        """
        if field_name not in self._original_values:
            return False
        return self._original_values[field_name] != getattr(self, field_name)

    @property
    def changed_fields(self) -> list[str]:
        """
        Get a list of all fields that have changed since initialization.

        Returns:
            list[str]: A list of field names that have different values than
                       when the instance was initialized. Returns an empty list
                       if no fields have changed.
        """
        changed = []
        for field, old_val in self._original_values.items():
            new_val = getattr(self, field)
            if old_val != new_val:
                changed.append(field)
        return changed

    @property
    def old_values(self) -> dict[str, Any]:
        """
        Get a dictionary of the original field values from initialization.

        Returns:
            dict: A dictionary mapping field names to their original values
                  as they were when the instance was initialized. Only includes
                  fields that are being tracked (either via TRACKED_FIELDS or
                  all non-deferred fields).
        """
        return self._original_values

    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Override save to automatically capture changed fields and reset tracking.

        Before saving, the current changed_fields are captured and stored in
        _changes_on_save. After saving, the tracked fields are reset so
        that subsequent saves correctly detect changes relative to the last
        saved state, not the original load-time state.

        Models that need to access the changed fields after save (e.g., for
        syncing related models) can use self._changes_on_save.
        """
        self._changes_on_save = self.changed_fields
        super().save(*args, **kwargs)
        self._reset_tracked_fields()

    def _reset_tracked_fields(self) -> None:
        """
        Reset the tracked field values to the current state.

        This is called automatically after save() to ensure that subsequent
        saves correctly detect changes relative to the last saved state,
        rather than the original load-time state.
        """
        self._original_values = {}
        self._track_fields()
