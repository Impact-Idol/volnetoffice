from django.urls import path
from plane.app.views.permissions import PermissionSyncEndpoint

urlpatterns = [
    # Permission Sync API
    path(
        "permissions/sync/",
        PermissionSyncEndpoint.as_view(),
        name="permission-sync",
    ),
]
