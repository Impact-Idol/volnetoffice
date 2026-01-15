"""
Permission Sync API

Synchronizes user permissions from Impact Idol to Plane workspaces
based on role and chapter assignments.
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from plane.app.views.base import BaseAPIView
from plane.db.models import User, Workspace, WorkspaceMember
from plane.db.models.workspace_extension import WorkspaceChapterMapping
from plane.utils.permission_bridge import (
    PlaneRole,
    map_role_to_plane,
    get_effective_workspace_role,
    should_have_workspace_access,
)
from plane.utils.exception_logger import log_exception


class PermissionSyncEndpoint(BaseAPIView):
    """
    Synchronizes user permissions based on Impact Idol role changes.

    POST /api/v1/permissions/sync/
    {
        "email": "user@example.com",
        "role": "CHAPTER_ADMIN",
        "chapters": [
            {"id": "clu123", "name": "Chapter Name", "isAdmin": true}
        ],
        "event": "role_change" | "chapter_assignment" | "full_sync"
    }

    This endpoint will:
    1. Find the user in Plane by email
    2. Calculate which workspaces they should have access to
    3. Update WorkspaceMember records with appropriate roles
    4. Remove access from workspaces they no longer qualify for
    """

    # Allow service-to-service calls without session auth
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # Validate service token (for service-to-service calls)
            auth_header = request.headers.get('Authorization', '')
            if not self._validate_service_token(auth_header):
                return Response(
                    {"error": "Invalid or missing service token"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Extract user data from request
            email = request.data.get('email')
            impact_idol_role = request.data.get('role')
            chapters = request.data.get('chapters', [])
            event_type = request.data.get('event', 'full_sync')

            if not email:
                return Response(
                    {"error": "Email is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not impact_idol_role:
                return Response(
                    {"error": "Role is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Perform sync
            result = sync_permissions_from_impact_idol({
                'email': email,
                'role': impact_idol_role,
                'chapters': chapters,
                'event': event_type,
            })

            return Response({
                'success': True,
                'synced_workspaces': result['synced_workspaces'],
                'removed_workspaces': result['removed_workspaces'],
                'event': event_type,
            })

        except User.DoesNotExist:
            return Response(
                {"error": "User not found in Plane"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            log_exception(e)
            return Response(
                {"error": "Permission sync failed", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _validate_service_token(self, auth_header: str) -> bool:
        """
        Validate the service token for service-to-service authentication.

        In production, this should check against PLANE_SERVICE_TOKEN env var.
        """
        from django.conf import settings

        if not auth_header.startswith('Bearer '):
            return False

        token = auth_header[7:]  # Remove 'Bearer ' prefix

        # Get service token from settings
        service_token = getattr(settings, 'PLANE_SERVICE_TOKEN', None)
        if not service_token:
            # If no service token configured, deny all requests
            return False

        return token == service_token


def sync_permissions_from_impact_idol(user_data: dict) -> dict:
    """
    Synchronize a user's workspace permissions based on their Impact Idol role.

    Args:
        user_data: Dict containing:
            - email: User's email address
            - role: Impact Idol role (SUPER_ADMIN, NONPROFIT_ADMIN, etc.)
            - chapters: List of chapter dicts with 'id', 'name', 'isAdmin'
            - event: Event type that triggered the sync

    Returns:
        Dict with sync results:
            - synced_workspaces: Number of workspaces synced
            - removed_workspaces: Number of workspaces removed
    """
    email = user_data['email']
    role = user_data['role']
    chapters = user_data.get('chapters', [])

    # Find user by email
    user = User.objects.get(email=email)

    # Extract chapter IDs from the chapters list
    user_chapter_ids = [c.get('id') for c in chapters if c.get('id')]

    synced = 0
    removed = 0

    # Handle based on role type
    if role in ('SUPER_ADMIN', 'NONPROFIT_ADMIN'):
        # Add to ALL workspaces as admin
        synced = _sync_all_workspaces(user, PlaneRole.ADMIN)

    elif role == 'CHAPTER_ADMIN':
        # Admin on chapter workspaces, Member on others
        synced, removed = _sync_chapter_admin_workspaces(user, chapters, user_chapter_ids)

    elif role == 'STAFF':
        # Member on all workspaces
        synced = _sync_all_workspaces(user, PlaneRole.MEMBER)

    else:
        # VOLUNTEER / MEMBER - Guest on chapter workspaces only
        synced, removed = _sync_guest_workspaces(user, user_chapter_ids)

    return {
        'synced_workspaces': synced,
        'removed_workspaces': removed,
    }


def _sync_all_workspaces(user: User, role: PlaneRole) -> int:
    """Add user to all workspaces with the specified role."""
    synced = 0
    for workspace in Workspace.objects.filter(deleted_at__isnull=True):
        WorkspaceMember.objects.update_or_create(
            workspace=workspace,
            member=user,
            deleted_at__isnull=True,
            defaults={
                'role': role.value,
                'is_active': True,
            }
        )
        synced += 1
    return synced


def _sync_chapter_admin_workspaces(user: User, chapters: list, user_chapter_ids: list) -> tuple:
    """
    Sync workspaces for CHAPTER_ADMIN role.
    - Admin on chapter workspaces where user is admin
    - Member on org-wide workspaces
    - Remove from workspaces where access is no longer valid
    """
    synced = 0
    removed = 0

    # Get chapter IDs where user is admin
    admin_chapter_ids = [c.get('id') for c in chapters if c.get('isAdmin', False)]

    for workspace in Workspace.objects.filter(deleted_at__isnull=True):
        # Check if workspace has chapter mapping
        try:
            mapping = workspace.chapter_mapping
        except WorkspaceChapterMapping.DoesNotExist:
            mapping = None

        # Determine role based on workspace type and chapter
        if mapping is None or mapping.workspace_type == 'org':
            # Org-wide workspace - give Member access
            WorkspaceMember.objects.update_or_create(
                workspace=workspace,
                member=user,
                deleted_at__isnull=True,
                defaults={
                    'role': PlaneRole.MEMBER.value,
                    'is_active': True,
                }
            )
            synced += 1

        elif mapping.chapter_id in admin_chapter_ids:
            # User is admin of this chapter - give Admin access
            WorkspaceMember.objects.update_or_create(
                workspace=workspace,
                member=user,
                deleted_at__isnull=True,
                defaults={
                    'role': PlaneRole.ADMIN.value,
                    'is_active': True,
                }
            )
            synced += 1

        elif mapping.has_chapter_access(user_chapter_ids):
            # User belongs to chapter but not admin - give Member access
            WorkspaceMember.objects.update_or_create(
                workspace=workspace,
                member=user,
                deleted_at__isnull=True,
                defaults={
                    'role': PlaneRole.MEMBER.value,
                    'is_active': True,
                }
            )
            synced += 1

        else:
            # User doesn't have access - remove membership
            deleted_count, _ = WorkspaceMember.objects.filter(
                workspace=workspace,
                member=user,
                deleted_at__isnull=True,
            ).delete()
            removed += deleted_count

    return synced, removed


def _sync_guest_workspaces(user: User, user_chapter_ids: list) -> tuple:
    """
    Sync workspaces for VOLUNTEER/MEMBER role.
    - Guest on org-wide workspaces
    - Guest on chapter workspaces where user is a member
    - Remove from other workspaces
    """
    synced = 0
    removed = 0

    for workspace in Workspace.objects.filter(deleted_at__isnull=True):
        # Check if workspace has chapter mapping
        try:
            mapping = workspace.chapter_mapping
        except WorkspaceChapterMapping.DoesNotExist:
            mapping = None

        # Determine access based on workspace type
        if mapping is None or mapping.workspace_type == 'org':
            # Org-wide workspace - give Guest access
            WorkspaceMember.objects.update_or_create(
                workspace=workspace,
                member=user,
                deleted_at__isnull=True,
                defaults={
                    'role': PlaneRole.GUEST.value,
                    'is_active': True,
                }
            )
            synced += 1

        elif mapping.has_chapter_access(user_chapter_ids):
            # User belongs to this chapter - give Guest access
            WorkspaceMember.objects.update_or_create(
                workspace=workspace,
                member=user,
                deleted_at__isnull=True,
                defaults={
                    'role': PlaneRole.GUEST.value,
                    'is_active': True,
                }
            )
            synced += 1

        else:
            # User doesn't have access - remove membership
            deleted_count, _ = WorkspaceMember.objects.filter(
                workspace=workspace,
                member=user,
                deleted_at__isnull=True,
            ).delete()
            removed += deleted_count

    return synced, removed
