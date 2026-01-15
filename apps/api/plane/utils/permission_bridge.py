"""
Permission Bridge Utility

Maps Impact Idol roles to Plane workspace roles and provides
cascading permission logic for chapter-scoped access control.
"""

from enum import IntEnum
from typing import List, Dict, Optional


class PlaneRole(IntEnum):
    """Plane workspace role values"""
    GUEST = 5
    VIEWER = 10
    MEMBER = 15
    ADMIN = 20


# Impact Idol role to Plane role mapping
ROLE_MAPPING = {
    'SUPER_ADMIN': PlaneRole.ADMIN,
    'NONPROFIT_ADMIN': PlaneRole.ADMIN,
    'CHAPTER_ADMIN': PlaneRole.ADMIN,  # Context-dependent (chapter workspaces only)
    'STAFF': PlaneRole.MEMBER,
    'MEMBER': PlaneRole.GUEST,  # Village member
    'VOLUNTEER': PlaneRole.GUEST,
}


def map_role_to_plane(impact_idol_role: str) -> PlaneRole:
    """
    Convert an Impact Idol role to the corresponding Plane role.

    Args:
        impact_idol_role: The Impact Idol role string (e.g., 'SUPER_ADMIN', 'VOLUNTEER')

    Returns:
        PlaneRole enum value
    """
    return ROLE_MAPPING.get(impact_idol_role, PlaneRole.GUEST)


def get_effective_workspace_role(
    user_id: str,
    impact_idol_role: str,
    chapters: List[Dict],
    workspace_slug: str,
    workspace_chapter_id: Optional[str] = None
) -> PlaneRole:
    """
    Calculate the effective role a user should have in a specific workspace
    based on their Impact Idol role and chapter assignments.

    Cascading rules:
    - SUPER_ADMIN → Admin on ALL workspaces
    - NONPROFIT_ADMIN → Admin on ALL workspaces
    - CHAPTER_ADMIN → Admin on their chapter workspace(s), Member elsewhere
    - STAFF → Member on ALL workspaces
    - VOLUNTEER/MEMBER → Guest on allowed workspaces

    Args:
        user_id: The user's ID
        impact_idol_role: The user's Impact Idol role
        chapters: List of chapter dicts with 'id' and optional 'isAdmin' flag
        workspace_slug: The Plane workspace slug
        workspace_chapter_id: The chapter ID linked to this workspace (if any)

    Returns:
        PlaneRole enum value representing the effective role
    """
    # SUPER_ADMIN and NONPROFIT_ADMIN get Admin everywhere
    if impact_idol_role in ('SUPER_ADMIN', 'NONPROFIT_ADMIN'):
        return PlaneRole.ADMIN

    # CHAPTER_ADMIN gets Admin only on their chapter workspaces
    if impact_idol_role == 'CHAPTER_ADMIN':
        # Get chapter IDs where user is admin
        admin_chapter_ids = [
            c.get('id') for c in chapters
            if c.get('isAdmin', False)
        ]

        # If workspace is linked to one of user's admin chapters, grant Admin
        if workspace_chapter_id and workspace_chapter_id in admin_chapter_ids:
            return PlaneRole.ADMIN

        # Otherwise, CHAPTER_ADMIN gets Member access
        return PlaneRole.MEMBER

    # STAFF gets Member access everywhere
    if impact_idol_role == 'STAFF':
        return PlaneRole.MEMBER

    # VOLUNTEER and MEMBER get Guest access
    return PlaneRole.GUEST


def should_have_workspace_access(
    impact_idol_role: str,
    user_chapter_ids: List[str],
    workspace_chapter_id: Optional[str] = None,
    workspace_type: str = 'org'
) -> bool:
    """
    Determine if a user should have any access to a workspace based on their
    role and chapter assignments.

    Args:
        impact_idol_role: The user's Impact Idol role
        user_chapter_ids: List of chapter IDs the user belongs to
        workspace_chapter_id: The chapter ID linked to this workspace (if any)
        workspace_type: Type of workspace ('org', 'chapter', 'cross')

    Returns:
        True if user should have access, False otherwise
    """
    # SUPER_ADMIN and NONPROFIT_ADMIN have access everywhere
    if impact_idol_role in ('SUPER_ADMIN', 'NONPROFIT_ADMIN'):
        return True

    # STAFF has access everywhere
    if impact_idol_role == 'STAFF':
        return True

    # Organization-wide workspaces are accessible to all
    if workspace_type == 'org':
        return True

    # Chapter-specific workspaces require chapter membership
    if workspace_type == 'chapter':
        if workspace_chapter_id and workspace_chapter_id in user_chapter_ids:
            return True
        return False

    # Cross-chapter workspaces - check if user belongs to any linked chapter
    # This would require additional_chapter_ids from WorkspaceChapterMapping
    if workspace_type == 'cross':
        if workspace_chapter_id and workspace_chapter_id in user_chapter_ids:
            return True
        return False

    return False


def get_role_display_name(role: PlaneRole) -> str:
    """Get human-readable name for a Plane role."""
    display_names = {
        PlaneRole.GUEST: 'Guest',
        PlaneRole.VIEWER: 'Viewer',
        PlaneRole.MEMBER: 'Member',
        PlaneRole.ADMIN: 'Admin',
    }
    return display_names.get(role, 'Unknown')
