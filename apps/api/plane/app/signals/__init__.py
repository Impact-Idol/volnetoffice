# Impact Idol Webhook Signal Handlers
#
# This module contains Django signal handlers that trigger webhooks
# to Impact Idol when certain events occur in Plane.
#
# Signals:
#   - IssueAssignee post_save: Notifies when a task is assigned
#   - Issue post_save (state change): Notifies when task status changes
#   - IssueComment post_save: Notifies on new comments
#   - IssueMention post_save: Notifies when user is mentioned

from .issues import *  # noqa: F401, F403
from .comments import *  # noqa: F401, F403
