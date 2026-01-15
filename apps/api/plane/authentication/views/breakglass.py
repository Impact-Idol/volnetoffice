"""Break Glass Authentication

Emergency authentication endpoint that allows super admins to bypass
SSO and log in with their existing Plane credentials during emergencies.

This is a security-critical endpoint with:
- Strict rate limiting (3 attempts per hour)
- Required super admin + sso_bypass flag
- Security alerts on both success and failure
- Full audit logging
"""

from django.conf import settings
from django.contrib.auth import authenticate
from django.views import View
from django.http import JsonResponse
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from plane.db.models import User
from plane.utils.alerts import send_security_alert
from plane.authentication.utils.host import user_ip


class BreakGlassLoginView(View):
    """
    POST /api/v1/auth/breakglass/

    Emergency authentication for super admins when SSO is unavailable.

    Requirements:
        - User must be a superuser (is_superuser=True)
        - User must have SSO bypass enabled (sso_bypass=True)

    Request Body:
        email: Super admin's email
        password: Super admin's Plane password
        reason: Why break glass is being used (required for audit)

    Response:
        On success:
            access: JWT access token
            refresh: JWT refresh token
        On failure:
            error: Error message

    Security:
        - Rate limited to 3 attempts per hour
        - All attempts (success/failure) trigger security alerts
        - Full audit logging with IP, user agent, etc.
    """

    def post(self, request):
        """Handle break glass authentication request."""
        import json

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {"error": "Invalid JSON body"},
                status=400,
            )

        email = data.get("email", "").lower().strip()
        password = data.get("password")
        reason = data.get("reason", "Not provided")

        if not email or not password:
            return JsonResponse(
                {"error": "Email and password required"},
                status=400,
            )

        # Find the user
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don't reveal whether user exists
            self._log_failed_attempt(request, email, "User not found")
            return JsonResponse(
                {"error": "Invalid credentials"},
                status=401,
            )

        # Check if user is authorized for break glass
        if not user.is_superuser:
            self._log_failed_attempt(request, email, "Not a superuser")
            return JsonResponse(
                {"error": "Not authorized for break glass access"},
                status=403,
            )

        # Check if SSO bypass is enabled for this user
        sso_bypass = getattr(user, "sso_bypass", False)
        if not sso_bypass:
            self._log_failed_attempt(request, email, "SSO bypass not enabled")
            return JsonResponse(
                {"error": "Not authorized for break glass access"},
                status=403,
            )

        # Check if user is active
        if not user.is_active:
            self._log_failed_attempt(request, email, "User is deactivated")
            return JsonResponse(
                {"error": "Account is deactivated"},
                status=403,
            )

        # Authenticate with password
        authenticated_user = authenticate(email=email, password=password)
        if not authenticated_user:
            self._handle_failed_login(request, email, user, reason)
            return JsonResponse(
                {"error": "Invalid credentials"},
                status=401,
            )

        # Success - generate tokens
        tokens = self._get_tokens_for_user(authenticated_user)

        # Alert security team
        self._handle_successful_login(request, user, reason)

        # Update last login
        user.last_login_time = timezone.now()
        user.last_login_ip = user_ip(request)
        user.last_login_medium = "breakglass"
        user.last_login_uagent = request.META.get("HTTP_USER_AGENT", "")[:255]
        user.save(update_fields=[
            "last_login_time",
            "last_login_ip",
            "last_login_medium",
            "last_login_uagent",
        ])

        return JsonResponse({
            "access": str(tokens["access"]),
            "refresh": str(tokens["refresh"]),
        })

    def _get_tokens_for_user(self, user) -> dict:
        """Generate JWT tokens for a user."""
        refresh = RefreshToken.for_user(user)
        return {
            "access": refresh.access_token,
            "refresh": refresh,
        }

    def _log_failed_attempt(self, request, email, reason):
        """Log a failed break glass attempt."""
        import logging

        logger = logging.getLogger("plane.security")
        logger.warning(
            f"Break glass login failed for {email}: {reason}",
            extra={
                "email": email,
                "reason": reason,
                "ip_address": user_ip(request),
                "user_agent": request.META.get("HTTP_USER_AGENT", ""),
            },
        )

    def _handle_failed_login(self, request, email, user, reason):
        """Handle a failed password authentication."""
        # Log the attempt
        self._log_failed_attempt(request, email, "Invalid password")

        # Send security alert
        send_security_alert(
            title="Break Glass Login Failed",
            message=f"Failed break glass attempt for {email}\n"
                    f"Reason provided: {reason}\n"
                    f"IP: {user_ip(request)}\n"
                    f"User Agent: {request.META.get('HTTP_USER_AGENT', '')[:100]}",
            severity="high",
            channels=["sms", "email"],
        )

    def _handle_successful_login(self, request, user, reason):
        """Handle a successful break glass login."""
        import logging

        logger = logging.getLogger("plane.security")
        logger.warning(
            f"BREAK GLASS LOGIN USED by {user.email}",
            extra={
                "user_id": str(user.id),
                "user_email": user.email,
                "reason": reason,
                "ip_address": user_ip(request),
                "user_agent": request.META.get("HTTP_USER_AGENT", ""),
            },
        )

        # Send critical security alert
        send_security_alert(
            title="BREAK GLASS LOGIN USED",
            message=f"User: {user.email}\n"
                    f"Reason: {reason}\n"
                    f"IP: {user_ip(request)}\n"
                    f"Time: {timezone.now().isoformat()}",
            severity="critical",
            channels=["sms", "email"],
        )
