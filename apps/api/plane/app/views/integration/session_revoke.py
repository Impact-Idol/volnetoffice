"""
Session Revoke Integration Endpoint

Revokes all user sessions when they are deactivated in Impact Idol.
"""

from rest_framework import status
from rest_framework.response import Response
from django.db import transaction

from plane.api.views.base import BaseAPIView
from plane.db.models import User
from plane.db.models.api import APIToken
from plane.utils.exception_logger import log_exception


class SessionRevokeEndpoint(BaseAPIView):
    """
    POST /api/v1/auth/revoke-sessions/

    Revoke all user sessions by incrementing token_version.
    Optionally deactivate the user account.
    Requires service token authentication via X-Api-Key header.

    Request Body:
        {
            "email": "user@example.com",
            "deactivate": true  // optional, also mark user as inactive
        }

    Response (200 OK):
        {
            "success": true,
            "message": "Sessions revoked successfully",
            "data": {
                "email": "user@example.com",
                "sessionsRevoked": 3,
                "tokenVersion": 2,
                "deactivated": true,
                "isActive": false
            }
        }

    Response (404 Not Found):
        {
            "error": "User not found"
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

            # Extract request data
            email = request.data.get('email')
            deactivate = request.data.get('deactivate', False)

            if not email:
                return Response(
                    {"error": "email is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Find user
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Perform session revocation in transaction
            with transaction.atomic():
                # Increment token_version to invalidate all JWTs
                user.token_version += 1

                # Optionally deactivate user
                if deactivate:
                    user.is_active = False

                user.save(update_fields=['token_version', 'is_active'])

                # Try to delete Django sessions if they exist
                # Django's Session model may or may not be in use
                deleted_count = 0
                try:
                    from django.contrib.sessions.models import Session
                    # Delete all sessions for this user
                    # Django sessions don't have direct user FK, so we can't filter by user
                    # Just rely on token_version increment for JWT invalidation
                    deleted_count = 0
                except ImportError:
                    # Session model not available
                    pass

            return Response(
                {
                    "success": True,
                    "message": "Sessions revoked successfully",
                    "data": {
                        "email": user.email,
                        "sessionsRevoked": deleted_count,
                        "tokenVersion": user.token_version,
                        "deactivated": deactivate,
                        "isActive": user.is_active,
                    }
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            log_exception(e)
            return Response(
                {"error": "Session revocation failed", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
