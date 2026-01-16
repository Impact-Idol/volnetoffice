"""Impact Idol SSO Authentication Bridge

This endpoint allows Impact Idol users to authenticate with Plane/VolNetOffice
using a JWT token exchange.

Security:
- JWT tokens are validated against IMPACTIDOL_JWT_SECRET
- Only users with ACTIVE status are allowed
- Only users with STAFF+ roles have Plane access
- Full audit logging for all authentication attempts
"""

import json
import logging

import jwt
from django.conf import settings
from django.contrib.auth import login as django_login
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from plane.db.models import User, Workspace, WorkspaceMember, Profile
from plane.authentication.utils.host import user_ip


logger = logging.getLogger("plane.security")


# Impact Idol roles that have Plane access
ALLOWED_ROLES = frozenset([
    "STAFF",
    "CHAPTER_ADMIN",
    "NONPROFIT_ADMIN",
    "SUPER_ADMIN",
])

# Map Impact Idol roles to Plane workspace roles
# Plane roles: 20=Admin, 15=Member, 5=Guest
ROLE_MAPPING = {
    "SUPER_ADMIN": 20,      # Plane Admin
    "NONPROFIT_ADMIN": 15,  # Plane Member
    "CHAPTER_ADMIN": 15,    # Plane Member
    "STAFF": 15,            # Plane Member
    "VOLUNTEER": 5,         # Plane Guest (shouldn't reach here)
}


@method_decorator(csrf_exempt, name="dispatch")
class ImpactIdolSSOView(View):
    """
    POST /auth/impactidol-sso/

    SSO authentication endpoint for Impact Idol users.

    Request Body:
        token: JWT token signed with shared secret containing:
            - sub: User ID in Impact Idol
            - email: User's email
            - name: User's display name
            - role: Impact Idol role (STAFF, CHAPTER_ADMIN, etc.)
            - status: Account status (must be ACTIVE)
            - iat: Issued at timestamp
            - exp: Expiration timestamp

    Response:
        On success:
            access_token: Plane JWT access token
            refresh_token: Plane JWT refresh token
            user: Object containing user details

        On failure:
            error: Error message
    """

    def post(self, request):
        """Handle SSO authentication request."""
        try:
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse(
                    {"error": "Invalid JSON body"},
                    status=400,
                )

            token = data.get("token")
            if not token:
                return JsonResponse(
                    {"error": "Token required"},
                    status=400,
                )

            # Validate JWT token
            jwt_secret = getattr(settings, "IMPACTIDOL_JWT_SECRET", None)
            if not jwt_secret:
                logger.error("IMPACTIDOL_JWT_SECRET not configured")
                return JsonResponse(
                    {"error": "SSO not configured"},
                    status=500,
                )

            try:
                payload = jwt.decode(
                    token,
                    jwt_secret,
                    algorithms=["HS256"],
                )
            except jwt.ExpiredSignatureError:
                self._log_auth_failure(request, None, "Token expired")
                return JsonResponse(
                    {"error": "Token expired"},
                    status=401,
                )
            except jwt.InvalidTokenError as e:
                self._log_auth_failure(request, None, f"Invalid token: {str(e)}")
                return JsonResponse(
                    {"error": f"Invalid token: {str(e)}"},
                    status=401,
                )

            # Extract payload fields
            email = payload.get("email", "").lower().strip()
            name = payload.get("name", "")
            role = payload.get("role", "")
            status = payload.get("status", "")
            impactidol_user_id = payload.get("sub", "")

            if not email:
                return JsonResponse(
                    {"error": "Email required in token"},
                    status=400,
                )

            # CRITICAL: Validate user status
            if status != "ACTIVE":
                self._log_auth_failure(
                    request,
                    email,
                    f"User account not active (status: {status})",
                )
                return JsonResponse(
                    {"error": "User account is not active"},
                    status=403,
                )

            # CRITICAL: Validate role has Plane access
            if role not in ALLOWED_ROLES:
                self._log_auth_failure(
                    request,
                    email,
                    f"Insufficient permissions (role: {role})",
                )
                return JsonResponse(
                    {"error": "Insufficient permissions for Plane access"},
                    status=403,
                )

            # Get or create Plane user
            # Generate username from email (before @ symbol)
            username = email.split("@")[0]

            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": username,
                    "first_name": self._extract_first_name(name),
                    "last_name": self._extract_last_name(name),
                    "display_name": name or username,
                    "is_active": True,
                    "is_email_verified": True,  # Trust Impact Idol verification
                },
            )

            # Ensure user is active (may have been deactivated previously)
            if not user.is_active:
                user.is_active = True
                user.save(update_fields=["is_active"])

            # Ensure user has a profile (required for frontend)
            # Mark SSO users as onboarded to skip onboarding flow
            if created or not hasattr(user, 'profile'):
                Profile.objects.get_or_create(
                    user=user,
                    defaults={
                        'is_onboarded': True,
                    }
                )
            else:
                # Update existing profile to mark as onboarded
                profile = user.profile
                if not profile.is_onboarded:
                    profile.is_onboarded = True
                    profile.save(update_fields=['is_onboarded'])

            # Sync user to default workspace with appropriate role
            self._sync_user_to_workspace(user, role)

            # Update last login info
            user.last_login_time = timezone.now()
            user.last_login_ip = user_ip(request)
            user.last_login_medium = "impactidol_sso"
            user.save(update_fields=[
                "last_login_time",
                "last_login_ip",
                "last_login_medium",
            ])

            # IMPORTANT: Ensure session is available
            # CSRF exempt views don't automatically create sessions
            if not request.session.session_key:
                request.session.create()

            # Log the user in using Django's session authentication
            # This creates a session and sets the sessionid cookie
            django_login(request, user, backend="django.contrib.auth.backends.ModelBackend")

            # Force session save to ensure it's persisted
            request.session.save()

            # Log successful authentication
            self._log_auth_success(request, user, created, impactidol_user_id)

            # Return success response with user info
            response = JsonResponse({
                "success": True,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "display_name": user.display_name,
                },
            })

            return response

        except Exception as e:
            # Log the full exception for debugging
            logger.exception(
                "Impact Idol SSO: Unexpected error during authentication",
                extra={"error": str(e)},
            )
            # Return generic error to user
            return JsonResponse(
                {"error": "Authentication failed"},
                status=500,
            )


    def _sync_user_to_workspace(self, user, impact_role: str):
        """
        Add/update user in the default workspace with appropriate role.
        """
        workspace_slug = getattr(
            settings,
            "DEFAULT_WORKSPACE_SLUG",
            getattr(settings, "PLANE_WORKSPACE_SLUG", "staff"),
        )

        workspace = Workspace.objects.filter(slug=workspace_slug).first()
        if not workspace:
            logger.warning(
                f"Default workspace '{workspace_slug}' not found for SSO user {user.email}"
            )
            return

        plane_role = ROLE_MAPPING.get(impact_role, 5)

        WorkspaceMember.objects.update_or_create(
            workspace=workspace,
            member=user,
            defaults={
                "role": plane_role,
                "is_active": True,
            },
        )

    def _extract_first_name(self, name: str) -> str:
        """Extract first name from full name."""
        if not name:
            return ""
        parts = name.strip().split()
        return parts[0] if parts else ""

    def _extract_last_name(self, name: str) -> str:
        """Extract last name from full name."""
        if not name:
            return ""
        parts = name.strip().split()
        return " ".join(parts[1:]) if len(parts) > 1 else ""

    def _log_auth_failure(self, request, email: str | None, reason: str):
        """Log a failed SSO authentication attempt."""
        logger.warning(
            f"Impact Idol SSO auth failed: {reason}",
            extra={
                "email": email,
                "reason": reason,
                "ip_address": user_ip(request),
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:255],
            },
        )

    def _log_auth_success(self, request, user, created: bool, impactidol_user_id: str):
        """Log a successful SSO authentication."""
        action = "created and authenticated" if created else "authenticated"
        logger.info(
            f"Impact Idol SSO: User {user.email} {action}",
            extra={
                "user_id": str(user.id),
                "user_email": user.email,
                "impactidol_user_id": impactidol_user_id,
                "user_created": created,
                "ip_address": user_ip(request),
            },
        )
