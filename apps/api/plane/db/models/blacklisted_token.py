"""Blacklisted Token Model for Session Revocation"""

import uuid
from django.db import models
from django.utils import timezone

from ..mixins import TimeAuditModel


class BlacklistedToken(TimeAuditModel):
    """
    Tracks blacklisted token versions for users.
    When a user's sessions are revoked, their token_version is incremented
    and recorded here for audit purposes.
    """

    id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        primary_key=True,
    )
    user = models.ForeignKey(
        "db.User",
        on_delete=models.CASCADE,
        related_name="blacklisted_tokens",
    )
    token_version = models.IntegerField(
        help_text="The token version that was blacklisted",
    )
    reason = models.CharField(
        max_length=255,
        default="Session revocation",
        help_text="Reason for blacklisting",
    )
    initiated_by = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Email of admin who initiated the revocation",
    )
    revoked_at = models.DateTimeField(
        default=timezone.now,
        help_text="When the tokens were revoked",
    )

    class Meta:
        verbose_name = "Blacklisted Token"
        verbose_name_plural = "Blacklisted Tokens"
        db_table = "blacklisted_tokens"
        ordering = ("-revoked_at",)
        indexes = [
            models.Index(fields=["user", "token_version"]),
        ]

    def __str__(self):
        return f"Blacklisted token v{self.token_version} for {self.user.email}"
