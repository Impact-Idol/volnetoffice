"""
User Lookup Integration Endpoint

Allows Impact Idol to check if a user exists before creating duplicate accounts.
"""

from rest_framework import status
from rest_framework.response import Response

from plane.api.views.base import BaseAPIView
from plane.db.models import User
from plane.db.models.api import APIToken
from plane.app.serializers import UserSerializer
from plane.utils.exception_logger import log_exception


class UserLookupEndpoint(BaseAPIView):
    """
    GET /api/v1/users/by-email/<email>/

    Lookup user by email address (case-insensitive).
    Returns user data if found, 404 if not found.
    Requires service token authentication via X-Api-Key header.

    URL Parameters:
        email: User's email address

    Response (200 OK):
        {
            "id": "uuid",
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "is_active": true,
            ...
        }

    Response (404 Not Found):
        {
            "error": "User not found"
        }
    """

    def get(self, request, email):
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

            # Case-insensitive email lookup
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Serialize user data
            serializer = UserSerializer(user)

            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )

        except Exception as e:
            log_exception(e)
            return Response(
                {"error": "User lookup failed", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
