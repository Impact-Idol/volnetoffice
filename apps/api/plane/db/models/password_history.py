"""
HIPAA Password History and Failed Login Tracking

This module provides models for enforcing HIPAA password requirements:
- Password history to prevent reuse
- Failed login tracking for account lockout
"""

import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import check_password, make_password
from django.conf import settings


class PasswordHistory(models.Model):
    """
    Tracks password history to prevent reuse.

    HIPAA requires preventing reuse of recent passwords.
    Default: 12 previous passwords cannot be reused.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        'db.User',
        on_delete=models.CASCADE,
        related_name='password_history'
    )
    password_hash = models.CharField(
        max_length=255,
        help_text="Hashed password for comparison"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )

    class Meta:
        db_table = 'password_history'
        ordering = ['-created_at']
        verbose_name = 'Password History'
        verbose_name_plural = 'Password Histories'

    @classmethod
    def add_password(cls, user, raw_password):
        """
        Add a password to history after user changes password.

        Args:
            user: User instance
            raw_password: The new raw (unhashed) password
        """
        # Create new history entry
        cls.objects.create(
            user=user,
            password_hash=make_password(raw_password)
        )

        # Prune old entries beyond the history count
        history_count = getattr(settings, 'HIPAA_PASSWORD_HISTORY_COUNT', 12)
        old_entries = cls.objects.filter(user=user).order_by('-created_at')[history_count:]
        for entry in old_entries:
            entry.delete()

    @classmethod
    def is_password_reused(cls, user, raw_password):
        """
        Check if password was recently used.

        Args:
            user: User instance
            raw_password: The password to check

        Returns:
            True if password matches any in history, False otherwise
        """
        history_count = getattr(settings, 'HIPAA_PASSWORD_HISTORY_COUNT', 12)
        recent_passwords = cls.objects.filter(user=user).order_by('-created_at')[:history_count]

        for entry in recent_passwords:
            if check_password(raw_password, entry.password_hash):
                return True

        return False


class FailedLoginAttempt(models.Model):
    """
    Tracks failed login attempts for account lockout.

    HIPAA requires account lockout after N failed attempts.
    Default: 5 failed attempts triggers 15-minute lockout.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Can track by user (if known) or by identifier (email/username)
    user = models.ForeignKey(
        'db.User',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='failed_logins'
    )
    identifier = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Email or username attempted"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        db_index=True
    )
    user_agent = models.TextField(
        blank=True
    )
    attempted_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    reason = models.CharField(
        max_length=50,
        default='invalid_password',
        choices=[
            ('invalid_password', 'Invalid Password'),
            ('user_not_found', 'User Not Found'),
            ('account_disabled', 'Account Disabled'),
            ('account_locked', 'Account Locked'),
            ('mfa_failed', 'MFA Failed'),
        ]
    )

    class Meta:
        db_table = 'failed_login_attempts'
        ordering = ['-attempted_at']
        verbose_name = 'Failed Login Attempt'
        verbose_name_plural = 'Failed Login Attempts'

    @classmethod
    def record_failure(cls, identifier, ip_address=None, user_agent='', user=None, reason='invalid_password'):
        """Record a failed login attempt"""
        return cls.objects.create(
            identifier=identifier,
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else '',
            user=user,
            reason=reason
        )

    @classmethod
    def is_locked_out(cls, identifier=None, ip_address=None):
        """
        Check if identifier or IP is currently locked out.

        Args:
            identifier: Email or username
            ip_address: IP address

        Returns:
            Tuple of (is_locked: bool, unlock_time: datetime or None)
        """
        threshold = getattr(settings, 'HIPAA_FAILED_LOGIN_THRESHOLD', 5)
        lockout_duration = getattr(settings, 'HIPAA_FAILED_LOGIN_LOCKOUT', 900)  # 15 minutes

        lockout_window = timezone.now() - timedelta(seconds=lockout_duration)

        # Build query for recent failures
        query = models.Q(attempted_at__gte=lockout_window)

        if identifier:
            query &= models.Q(identifier=identifier)
        elif ip_address:
            query &= models.Q(ip_address=ip_address)
        else:
            return False, None

        recent_failures = cls.objects.filter(query).count()

        if recent_failures >= threshold:
            # Find when the oldest failure in window occurred
            oldest_in_window = cls.objects.filter(query).order_by('attempted_at').first()
            if oldest_in_window:
                unlock_time = oldest_in_window.attempted_at + timedelta(seconds=lockout_duration)
                return True, unlock_time

        return False, None

    @classmethod
    def clear_failures(cls, identifier):
        """Clear failed attempts after successful login"""
        # Only clear recent failures (within lockout window)
        lockout_duration = getattr(settings, 'HIPAA_FAILED_LOGIN_LOCKOUT', 900)
        cutoff = timezone.now() - timedelta(seconds=lockout_duration)

        cls.objects.filter(
            identifier=identifier,
            attempted_at__gte=cutoff
        ).delete()

    @classmethod
    def cleanup_old_records(cls, days=30):
        """Remove old failure records for maintenance"""
        cutoff = timezone.now() - timedelta(days=days)
        return cls.objects.filter(attempted_at__lt=cutoff).delete()


class AccountLockout(models.Model):
    """
    Explicit account lockout tracking.

    Provides a separate record of when accounts are locked/unlocked.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        'db.User',
        on_delete=models.CASCADE,
        related_name='lockouts'
    )
    locked_at = models.DateTimeField(
        auto_now_add=True
    )
    locked_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the lockout expires (null = manual unlock required)"
    )
    reason = models.CharField(
        max_length=50,
        default='failed_logins',
        choices=[
            ('failed_logins', 'Too Many Failed Login Attempts'),
            ('admin_action', 'Administrative Action'),
            ('security_incident', 'Security Incident'),
            ('suspicious_activity', 'Suspicious Activity'),
        ]
    )
    unlocked_at = models.DateTimeField(
        null=True,
        blank=True
    )
    unlocked_by_id = models.UUIDField(
        null=True,
        blank=True
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True
    )

    class Meta:
        db_table = 'account_lockouts'
        ordering = ['-locked_at']
        verbose_name = 'Account Lockout'
        verbose_name_plural = 'Account Lockouts'

    def is_currently_locked(self):
        """Check if lockout is currently in effect"""
        if not self.is_active:
            return False
        if self.locked_until and self.locked_until < timezone.now():
            return False
        return True

    def unlock(self, unlocked_by_id=None):
        """Release the lockout"""
        self.is_active = False
        self.unlocked_at = timezone.now()
        self.unlocked_by_id = unlocked_by_id
        self.save()

    @classmethod
    def get_active_lockout(cls, user):
        """Get active lockout for user if any"""
        lockout = cls.objects.filter(
            user=user,
            is_active=True
        ).first()

        if lockout and lockout.is_currently_locked():
            return lockout

        # Auto-expire if time-based lockout has passed
        if lockout and lockout.locked_until and lockout.locked_until < timezone.now():
            lockout.is_active = False
            lockout.save()
            return None

        return lockout if lockout and lockout.is_currently_locked() else None
