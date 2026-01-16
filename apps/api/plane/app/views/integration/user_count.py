"""
User Count Integration Endpoint

Provides user count for Impact Idol dashboard sync validation.
"""

from rest_framework import status
from rest_framework.response import Response

from plane.api.views.base import BaseAPIView
from plane.db.models import User
from plane.db.models.api import APIToken
from plane.utils.exception_logger import log_exception


class UserCountEndpoint(BaseAPIView):
    """
    GET /api/v1/users/count/?is_active=true

    Returns count of users filtered by is_active status.
    Requires service token authentication via X-Api-Key header.

    Query Parameters:
        is_active (optional): Filter by active status. Default: 'true'

    Response:
        {
            "count": <number>
        }
    """

    def get(self, request):
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

            # Parse query parameter
            is_active_param = request.GET.get('is_active', 'true').lower()
            is_active = is_active_param == 'true'

            # Query database
            count = User.objects.filter(is_active=is_active).count()

            return Response(
                {"count": count},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            log_exception(e)
            return Response(
                {"error": "Failed to retrieve user count"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
