"""JWT Token Blacklisting Utilities"""

from django.core.cache import cache
from django.utils import timezone

from plane.db.models import User


def blacklist_user_tokens(user: User, reason: str = "Session revocation", initiated_by: str = None) -> int:
    """
    Blacklist all tokens for a user by incrementing their token_version.

    This invalidates all existing JWTs for the user since they will have
    a lower token_version than the current one.

    Args:
        user: The User instance to blacklist tokens for
        reason: Why the tokens are being blacklisted
        initiated_by: Email of the admin who initiated the action

    Returns:
        Number of token versions blacklisted (always 1)
    """
    # Import here to avoid circular imports
    from plane.db.models import BlacklistedToken

    # Increment the user's token version
    current_version = getattr(user, 'token_version', None) or 0
    new_version = current_version + 1

    # Update user's token version
    User.objects.filter(id=user.id).update(token_version=new_version)

    # Update cache for fast token validation
    cache_key = f"token_blacklist:user:{user.id}"
    cache.set(cache_key, new_version, timeout=86400 * 7)  # 7 days

    # Create audit record
    BlacklistedToken.objects.create(
        user=user,
        token_version=new_version,
        reason=reason,
        initiated_by=initiated_by,
        revoked_at=timezone.now(),
    )

    return 1


def is_token_blacklisted(user_id: str, token_version: int) -> bool:
    """
    Check if a token is blacklisted based on its version.

    A token is blacklisted if its version is less than the user's
    current token_version (meaning tokens were revoked after it was issued).

    Args:
        user_id: The user's ID (UUID as string)
        token_version: The token_version claim from the JWT

    Returns:
        True if the token is blacklisted (invalid), False otherwise
    """
    cache_key = f"token_blacklist:user:{user_id}"
    current_version = cache.get(cache_key)

    if current_version is None:
        # Cache miss - fetch from database
        try:
            user = User.objects.get(id=user_id)
            current_version = getattr(user, 'token_version', None) or 0
            cache.set(cache_key, current_version, timeout=3600)  # 1 hour
        except User.DoesNotExist:
            # User doesn't exist - token is invalid
            return True

    # Token is blacklisted if its version is less than the current version
    return token_version < current_version


def get_user_token_version(user: User) -> int:
    """
    Get the current token version for a user.

    Args:
        user: The User instance

    Returns:
        The user's current token_version (0 if not set)
    """
    return getattr(user, 'token_version', None) or 0
