"""
Comment-related signal handlers for Impact Idol webhooks.

Handles:
- New comment notifications (to issue assignees)
- Mention notifications (to mentioned users)
"""

import logging
import re
from typing import List, Set

from django.db.models.signals import post_save
from django.dispatch import receiver

from plane.db.models import IssueComment, IssueAssignee, IssueMention, User
from plane.bgtasks.webhook_task import (
    send_impactidol_issue_comment,
    send_impactidol_mentioned,
)


logger = logging.getLogger("plane.signals")

# Pattern to match @mentions in comment text
# Matches: @email@example.com or @username patterns
MENTION_PATTERN = re.compile(r'@([\w.+-]+@[\w.-]+\.\w+)', re.IGNORECASE)


def extract_mentions_from_text(text: str) -> Set[str]:
    """
    Extract email addresses from @mentions in text.

    Args:
        text: Comment text that may contain @email mentions

    Returns:
        Set of email addresses found in mentions
    """
    if not text:
        return set()

    matches = MENTION_PATTERN.findall(text)
    return set(email.lower() for email in matches)


@receiver(post_save, sender=IssueComment)
def handle_comment_created(sender, instance: IssueComment, created: bool, **kwargs):
    """
    Send webhooks when a comment is created on an issue.

    - Notifies all issue assignees about the new comment
    - Parses comment text for @mentions and notifies mentioned users

    Triggers:
    - issue.comment.created event (to assignees)
    - issue.mentioned event (to mentioned users)
    """
    if not created:
        # Only notify on new comments, not edits
        return

    # Skip if soft-deleted
    if instance.deleted_at is not None:
        return

    try:
        issue = instance.issue
        actor = instance.actor

        # Get actor name
        actor_name = 'Someone'
        if actor:
            actor_name = actor.display_name or actor.email or 'Someone'

        # Get comment preview (first 200 chars of stripped text)
        comment_preview = instance.comment_stripped[:200] if instance.comment_stripped else ''

        # Get all assignees to notify about the comment
        assignees = IssueAssignee.objects.filter(
            issue=issue,
            deleted_at__isnull=True,
        ).select_related('assignee')

        notified_emails: Set[str] = set()

        # Notify assignees (except the commenter)
        for issue_assignee in assignees:
            assignee = issue_assignee.assignee
            if not assignee or not assignee.email:
                continue

            # Don't notify the person who made the comment
            if actor and assignee.id == actor.id:
                continue

            email = assignee.email.lower()
            if email in notified_emails:
                continue

            send_impactidol_issue_comment(
                issue_id=str(issue.id),
                target_email=assignee.email,
                actor_name=actor_name,
                comment_preview=comment_preview,
            )
            notified_emails.add(email)
            logger.info(
                f"Comment notification queued for issue {issue.id} "
                f"to {assignee.email}"
            )

        # Parse mentions from comment text and notify mentioned users
        mentioned_emails = extract_mentions_from_text(instance.comment_stripped)

        for email in mentioned_emails:
            # Skip if already notified as assignee
            if email in notified_emails:
                continue

            # Verify user exists
            try:
                mentioned_user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                logger.debug(f"Mentioned user not found: {email}")
                continue

            # Don't notify the commenter if they mentioned themselves
            if actor and mentioned_user.id == actor.id:
                continue

            send_impactidol_mentioned(
                issue_id=str(issue.id),
                mentioned_email=mentioned_user.email,
                actor_name=actor_name,
            )
            notified_emails.add(email)
            logger.info(
                f"Mention notification queued for issue {issue.id} "
                f"to {mentioned_user.email}"
            )

    except Exception as e:
        logger.error(f"Failed to send comment notification: {e}")


@receiver(post_save, sender=IssueMention)
def handle_explicit_mention(sender, instance: IssueMention, created: bool, **kwargs):
    """
    Send webhook when a user is explicitly mentioned in an issue.

    This handles mentions created via the IssueMention model
    (separate from inline @mentions in comments).

    Triggers: issue.mentioned event
    """
    if not created:
        return

    # Skip if soft-deleted
    if instance.deleted_at is not None:
        return

    try:
        mentioned_user = instance.mention
        if not mentioned_user or not mentioned_user.email:
            logger.warning(f"Mentioned user missing email for IssueMention {instance.pk}")
            return

        # Get actor name (who created the mention)
        actor_name = 'Someone'
        if instance.created_by:
            # Don't notify if user mentioned themselves
            if instance.created_by.id == mentioned_user.id:
                return
            actor_name = instance.created_by.display_name or instance.created_by.email

        send_impactidol_mentioned(
            issue_id=str(instance.issue_id),
            mentioned_email=mentioned_user.email,
            actor_name=actor_name,
        )
        logger.info(
            f"Explicit mention notification queued for issue {instance.issue_id} "
            f"to {mentioned_user.email}"
        )
    except Exception as e:
        logger.error(f"Failed to send mention notification: {e}")
