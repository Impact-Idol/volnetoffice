"""
Workspace Extension Models

Links Plane workspaces to Impact Idol chapters for
role-based access control and permission cascading.
"""

from django.db import models

from .base import BaseModel


class WorkspaceChapterMapping(BaseModel):
    """
    Links Plane workspaces to Impact Idol chapters.

    This enables chapter-scoped permissions where:
    - CHAPTER_ADMIN users get Admin access only to workspaces
      linked to their chapters
    - VOLUNTEER users get Guest access only to workspaces
      linked to chapters they belong to
    """

    workspace = models.OneToOneField(
        "db.Workspace",
        on_delete=models.CASCADE,
        related_name="chapter_mapping",
    )

    # Impact Idol chapter ID (cuid format)
    chapter_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text="Primary Impact Idol chapter ID linked to this workspace",
    )

    chapter_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Chapter name for display purposes",
    )

    class WorkspaceType(models.TextChoices):
        ORG = "org", "Organization-wide"
        CHAPTER = "chapter", "Chapter-specific"
        CROSS = "cross", "Cross-chapter"

    workspace_type = models.CharField(
        max_length=20,
        choices=WorkspaceType.choices,
        default=WorkspaceType.ORG,
        help_text="Type of workspace for permission scoping",
    )

    # For cross-chapter workspaces that span multiple chapters
    additional_chapter_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="Additional chapter IDs for cross-chapter workspaces",
    )

    class Meta:
        verbose_name = "Workspace Chapter Mapping"
        verbose_name_plural = "Workspace Chapter Mappings"
        db_table = "workspace_chapter_mappings"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.workspace.name} -> {self.chapter_name or 'Org-wide'}"

    def has_chapter_access(self, chapter_ids: list) -> bool:
        """
        Check if a user with the given chapter IDs has access to this workspace.

        Args:
            chapter_ids: List of chapter IDs the user belongs to

        Returns:
            True if user has access, False otherwise
        """
        # Organization-wide workspaces are accessible to all
        if self.workspace_type == self.WorkspaceType.ORG:
            return True

        # Check if workspace's primary chapter is in user's chapters
        if self.chapter_id and self.chapter_id in chapter_ids:
            return True

        # For cross-chapter workspaces, check additional chapter IDs
        if self.workspace_type == self.WorkspaceType.CROSS:
            return any(cid in self.additional_chapter_ids for cid in chapter_ids)

        return False

    def get_all_chapter_ids(self) -> list:
        """
        Get all chapter IDs associated with this workspace.

        Returns:
            List of chapter IDs (primary + additional)
        """
        chapter_ids = []
        if self.chapter_id:
            chapter_ids.append(self.chapter_id)
        chapter_ids.extend(self.additional_chapter_ids or [])
        return chapter_ids
