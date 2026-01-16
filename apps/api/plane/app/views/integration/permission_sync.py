"""
Permission Sync Integration Endpoint

Synchronizes workspace permissions from Impact Idol to VolNetOffice.
"""

from rest_framework import status
from rest_framework.response import Response

from plane.api.views.base import BaseAPIView
from plane.db.models import User, Workspace, WorkspaceMember
from plane.db.models.api import APIToken
from plane.utils.exception_logger import log_exception


class PermissionSyncEndpoint(BaseAPIView):
    """
    POST /api/v1/permissions/sync/

    Synchronize workspace permissions from Impact Idol.
    Updates or creates WorkspaceMember with specified role.
    Requires service token authentication via X-Api-Key header.

    Request Body:
        {
            "userId": "550e8400-e29b-41d4-a716-446655440000",
            "workspaceSlug": "chapter-sf",
            "role": 20,  // 20=Admin, 15=Member, 5=Guest
            "isActive": true
        }

    Response (200 OK):
        {
            "success": true,
            "message": "Permission synced successfully",
            "data": {
                "userId": "550e8400-e29b-41d4-a716-446655440000",
                "workspaceSlug": "chapter-sf",
                "role": 20,
                "isActive": true,
                "created": false
            }
        }

    Response (400 Bad Request):
        {
            "error": "userId, workspaceSlug, and role are required"
        }

    Response (404 Not Found):
        {
            "error": "User not found" or "Workspace not found"
        }
    """

    def post(self, request):
        try:
            # Verify service token (extra security layer)
            # Support both X-Api-Key and X-Service-Token headers
            api_key = request.META.get('HTTP_X_API_KEY') or request.META.get('HTTP_X_SERVICE_TOKEN')
            token = APIToken.objects.filter(token=api_key, is_service=True).first()

            if not token:
                return Response(
                    {"error": "This endpoint requires a service token"},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Extract and validate request data
            user_id = request.data.get('userId')
            workspace_slug = request.data.get('workspaceSlug')
            role = request.data.get('role')
            is_active = request.data.get('isActive', True)

            if not all([user_id, workspace_slug, role is not None]):
                return Response(
                    {"error": "userId, workspaceSlug, and role are required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate role value
            valid_roles = [5, 15, 20]  # Guest, Member, Admin
            if role not in valid_roles:
                return Response(
                    {"error": "role must be 5 (Guest), 15 (Member), or 20 (Admin)"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Find user and workspace
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            try:
                workspace = Workspace.objects.get(slug=workspace_slug)
            except Workspace.DoesNotExist:
                return Response(
                    {"error": "Workspace not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Update or create WorkspaceMember
            workspace_member, created = WorkspaceMember.objects.update_or_create(
                workspace=workspace,
                member=user,
                defaults={
                    'role': role,
                    'is_active': is_active,
                }
            )

            return Response(
                {
                    "success": True,
                    "message": "Permission synced successfully",
                    "data": {
                        "userId": str(user.id),
                        "workspaceSlug": workspace.slug,
                        "role": workspace_member.role,
                        "isActive": workspace_member.is_active,
                        "created": created,
                    }
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            log_exception(e)
            return Response(
                {"error": "Permission sync failed", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
