"""
Issue-related signal handlers for Impact Idol webhooks.

Handles:
- Issue assignment notifications
- Issue status change notifications
"""

import logging
from typing import Optional

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from plane.db.models import Issue, IssueAssignee, State
from plane.bgtasks.webhook_task import (
    send_impactidol_issue_assigned,
    send_impactidol_status_changed,
)


logger = logging.getLogger("plane.signals")


# Cache to track state changes (cleared after each save)
_issue_state_cache: dict = {}


@receiver(pre_save, sender=Issue)
def cache_issue_state(sender, instance: Issue, **kwargs):
    """
    Cache the previous state before save to detect status changes.
    """
    if instance.pk:
        try:
            old_instance = Issue.objects.select_related('state').get(pk=instance.pk)
            _issue_state_cache[instance.pk] = {
                'old_state_id': old_instance.state_id,
                'old_state_name': old_instance.state.name if old_instance.state else None,
            }
        except Issue.DoesNotExist:
            pass


@receiver(post_save, sender=Issue)
def handle_issue_status_change(sender, instance: Issue, created: bool, **kwargs):
    """
    Send webhook when issue status changes.

    Triggers: issue.status.changed event
    """
    if created:
        # New issues don't trigger status change notifications
        _issue_state_cache.pop(instance.pk, None)
        return

    cached = _issue_state_cache.pop(instance.pk, None)
    if not cached:
        return

    old_state_id = cached.get('old_state_id')
    new_state_id = instance.state_id

    # Only notify if state actually changed
    if old_state_id == new_state_id:
        return

    # Get new state name
    new_state_name = instance.state.name if instance.state else 'Unknown'

    # Notify all assignees of the status change
    try:
        assignees = IssueAssignee.objects.filter(
            issue=instance,
            deleted_at__isnull=True,
        ).select_related('assignee')

        for issue_assignee in assignees:
            if issue_assignee.assignee and issue_assignee.assignee.email:
                send_impactidol_status_changed(
                    issue_id=str(instance.pk),
                    assignee_email=issue_assignee.assignee.email,
                    new_status=new_state_name,
                )
                logger.info(
                    f"Status change notification queued for issue {instance.pk} "
                    f"to {issue_assignee.assignee.email}"
                )
    except Exception as e:
        logger.error(f"Failed to send status change notification: {e}")


@receiver(post_save, sender=IssueAssignee)
def handle_issue_assignment(sender, instance: IssueAssignee, created: bool, **kwargs):
    """
    Send webhook when a user is assigned to an issue.

    Triggers: issue.assigned event
    """
    if not created:
        # Only notify on new assignments, not updates
        return

    # Skip if soft-deleted
    if instance.deleted_at is not None:
        return

    try:
        assignee = instance.assignee
        if not assignee or not assignee.email:
            logger.warning(f"Assignee missing email for IssueAssignee {instance.pk}")
            return

        # Get actor name (who made the assignment)
        actor_name = 'Someone'
        if instance.created_by:
            actor_name = instance.created_by.display_name or instance.created_by.email

        send_impactidol_issue_assigned(
            issue_id=str(instance.issue_id),
            assignee_email=assignee.email,
            actor_name=actor_name,
        )
        logger.info(
            f"Assignment notification queued for issue {instance.issue_id} "
            f"to {assignee.email}"
        )
    except Exception as e:
        logger.error(f"Failed to send assignment notification: {e}")
