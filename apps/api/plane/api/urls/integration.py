"""
Integration URL Patterns for /api/v1/ namespace

Re-exports integration endpoints from plane.app.views.integration
to make them available under both /api/ and /api/v1/ paths.
"""

from django.urls import path

from plane.app.views.integration import (
    UserCountEndpoint,
    UserLookupEndpoint,
    PermissionSyncEndpoint,
    SessionRevokeEndpoint,
)

urlpatterns = [
    # User Count - GET /api/v1/users/count/?is_active=true
    path(
        "users/count/",
        UserCountEndpoint.as_view(),
        name="api-integration-user-count",
    ),

    # User Lookup by Email - GET /api/v1/users/by-email/<email>/
    path(
        "users/by-email/<str:email>/",
        UserLookupEndpoint.as_view(),
        name="api-integration-user-lookup",
    ),

    # Permission Sync - POST /api/v1/permissions/sync/
    path(
        "permissions/sync/",
        PermissionSyncEndpoint.as_view(),
        name="api-integration-permission-sync",
    ),

    # Session Revocation - POST /api/v1/auth/revoke-sessions/
    path(
        "auth/revoke-sessions/",
        SessionRevokeEndpoint.as_view(),
        name="api-integration-session-revoke",
    ),
]
