"""
HIPAA Session Management Middleware

This middleware enforces HIPAA session requirements:
- Inactivity timeout (default: 15 minutes)
- Maximum session duration (default: 8 hours)
- Concurrent session limits
"""

import logging
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import logout

logger = logging.getLogger('plane.audit')


class HIPAASessionMiddleware:
    """
    Middleware to enforce HIPAA session timeouts.

    Must be placed after Django's SessionMiddleware and AuthenticationMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only process for authenticated users
        if hasattr(request, 'user') and request.user.is_authenticated:
            if self._should_terminate_session(request):
                self._terminate_session(request)

        response = self.get_response(request)

        # Update activity timestamp on successful requests
        if hasattr(request, 'user') and request.user.is_authenticated:
            self._update_activity(request)

        return response

    def _should_terminate_session(self, request):
        """Check if session should be terminated due to timeout"""
        # Get timeout settings
        inactivity_timeout = getattr(
            settings, 'HIPAA_SESSION_INACTIVITY_TIMEOUT', 900
        )
        max_session_age = getattr(
            settings, 'HIPAA_SESSION_MAX_AGE', 28800
        )

        current_time = timezone.now().timestamp()

        # Check inactivity timeout
        last_activity = request.session.get('hipaa_last_activity')
        if last_activity:
            inactive_duration = current_time - last_activity
            if inactive_duration > inactivity_timeout:
                logger.info(
                    f"Session timeout: inactivity ({inactive_duration}s) for user {request.user.id}"
                )
                return True

        # Check maximum session duration
        session_start = request.session.get('hipaa_session_start')
        if session_start:
            session_duration = current_time - session_start
            if session_duration > max_session_age:
                logger.info(
                    f"Session timeout: max age ({session_duration}s) for user {request.user.id}"
                )
                return True

        return False

    def _terminate_session(self, request):
        """Terminate the session and log the event"""
        from plane.utils.audit import create_audit_log

        user_id = request.user.id

        # Log the session termination
        create_audit_log(
            action='SESSION_TERMINATED_TIMEOUT',
            request=request,
            metadata={
                'reason': 'hipaa_timeout',
                'last_activity': request.session.get('hipaa_last_activity'),
                'session_start': request.session.get('hipaa_session_start'),
            }
        )

        # Logout the user
        logout(request)

        logger.info(f"Session terminated for user {user_id} due to HIPAA timeout")

    def _update_activity(self, request):
        """Update session activity timestamps"""
        current_time = timezone.now().timestamp()

        # Set session start if not set
        if 'hipaa_session_start' not in request.session:
            request.session['hipaa_session_start'] = current_time

        # Always update last activity
        request.session['hipaa_last_activity'] = current_time


class ConcurrentSessionMiddleware:
    """
    Middleware to enforce concurrent session limits.

    Terminates oldest sessions when limit is exceeded.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            self._enforce_session_limit(request)

        return self.get_response(request)

    def _enforce_session_limit(self, request):
        """Enforce maximum concurrent sessions"""
        from plane.db.models import Session

        max_sessions = getattr(settings, 'HIPAA_MAX_CONCURRENT_SESSIONS', 3)

        # Count active sessions for this user
        active_sessions = Session.objects.filter(
            user_id=request.user.id,
            is_active=True
        ).order_by('-created_at')

        # If over limit, deactivate oldest sessions
        if active_sessions.count() > max_sessions:
            sessions_to_deactivate = active_sessions[max_sessions:]

            for session in sessions_to_deactivate:
                session.is_active = False
                session.save()

                logger.info(
                    f"Deactivated oldest session {session.id} for user {request.user.id} "
                    f"due to concurrent session limit"
                )


class FailedLoginMiddleware:
    """
    Middleware to check for account lockouts before authentication.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only check on login endpoints
        if self._is_login_request(request):
            lockout_response = self._check_lockout(request)
            if lockout_response:
                return lockout_response

        return self.get_response(request)

    def _is_login_request(self, request):
        """Check if this is a login attempt"""
        login_paths = [
            '/api/v1/sign-in/',
            '/api/v1/login/',
            '/auth/login/',
        ]
        return request.method == 'POST' and any(
            request.path.startswith(path) for path in login_paths
        )

    def _check_lockout(self, request):
        """Check if the request should be blocked due to lockout"""
        from plane.db.models.password_history import FailedLoginAttempt
        from django.http import JsonResponse

        # Get identifier from request body
        import json
        try:
            body = json.loads(request.body.decode('utf-8'))
            identifier = body.get('email') or body.get('username')
        except (json.JSONDecodeError, UnicodeDecodeError):
            identifier = None

        ip_address = self._get_client_ip(request)

        # Check lockout by identifier
        if identifier:
            is_locked, unlock_time = FailedLoginAttempt.is_locked_out(identifier=identifier)
            if is_locked:
                logger.warning(
                    f"Login blocked: account lockout for {identifier}"
                )
                return JsonResponse({
                    'error': 'Account temporarily locked due to too many failed login attempts.',
                    'unlock_time': unlock_time.isoformat() if unlock_time else None,
                }, status=429)

        # Check lockout by IP
        if ip_address:
            is_locked, unlock_time = FailedLoginAttempt.is_locked_out(ip_address=ip_address)
            if is_locked:
                logger.warning(
                    f"Login blocked: IP lockout for {ip_address}"
                )
                return JsonResponse({
                    'error': 'Too many failed login attempts from this IP address.',
                    'unlock_time': unlock_time.isoformat() if unlock_time else None,
                }, status=429)

        return None

    def _get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
