"""
HIPAA-Compliant Permissions

This module provides permission classes that enforce HIPAA access control
requirements, including MFA verification and comprehensive audit logging.
"""

from rest_framework.permissions import BasePermission
from rest_framework import status
from django.conf import settings
from django.utils import timezone


class HIPAABasePermission(BasePermission):
    """
    Base permission class that logs all access attempts.

    This ensures comprehensive audit logging for HIPAA compliance,
    tracking both successful and failed access attempts.
    """

    message = 'Access denied.'

    def has_permission(self, request, view):
        """Log access attempt and delegate to subclass"""
        # Import here to avoid circular imports
        from plane.utils.audit import create_audit_log

        # Log the access attempt
        create_audit_log(
            action=f'ACCESS_ATTEMPT_{view.__class__.__name__}',
            request=request,
            metadata={
                'path': request.path,
                'method': request.method,
                'view': view.__class__.__name__,
            }
        )

        return True

    def has_object_permission(self, request, view, obj):
        """Log object-level access attempt"""
        from plane.utils.audit import create_audit_log

        resource_type = obj.__class__.__name__
        resource_id = getattr(obj, 'id', None) or getattr(obj, 'pk', None)

        create_audit_log(
            action=f'OBJECT_ACCESS_{view.__class__.__name__}',
            request=request,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata={
                'path': request.path,
                'method': request.method,
            }
        )

        return True


class RequireMFA(HIPAABasePermission):
    """
    Permission class that requires MFA verification for PHI access.

    Users must have completed MFA verification within the configured
    validity period to access protected resources.
    """

    message = 'Multi-factor authentication required for this resource.'

    def has_permission(self, request, view):
        """Check MFA status before allowing access"""
        # Call parent to log access attempt
        super().has_permission(request, view)

        # Unauthenticated users are denied
        if not request.user.is_authenticated:
            return False

        # Check if MFA is required (can be disabled for development)
        require_mfa = getattr(settings, 'HIPAA_REQUIRE_MFA_FOR_PHI', True)
        if not require_mfa:
            return True

        # Check MFA verification status in session
        mfa_verified = request.session.get('mfa_verified', False)
        if not mfa_verified:
            return False

        # Check MFA session validity
        mfa_verified_at = request.session.get('mfa_verified_at')
        if mfa_verified_at:
            validity_period = getattr(settings, 'HIPAA_MFA_SESSION_VALIDITY', 3600)
            mfa_expiry = mfa_verified_at + validity_period

            if timezone.now().timestamp() > mfa_expiry:
                # MFA session expired, require re-verification
                request.session['mfa_verified'] = False
                return False

        return True


class RequirePHIAccess(HIPAABasePermission):
    """
    Permission class for resources containing PHI.

    Combines MFA requirement with enhanced PHI access logging.
    """

    message = 'You do not have permission to access protected health information.'

    def has_permission(self, request, view):
        """Check PHI access permissions"""
        from plane.utils.audit import create_audit_log

        # Call parent to log access attempt
        super().has_permission(request, view)

        # Unauthenticated users are denied
        if not request.user.is_authenticated:
            return False

        # Check MFA requirement
        require_mfa = getattr(settings, 'HIPAA_REQUIRE_MFA_FOR_PHI', True)
        if require_mfa:
            mfa_verified = request.session.get('mfa_verified', False)
            if not mfa_verified:
                create_audit_log(
                    action='PHI_ACCESS_DENIED_NO_MFA',
                    request=request,
                    phi_accessed=False,
                    metadata={'reason': 'MFA not verified'}
                )
                return False

        # Log PHI access attempt
        create_audit_log(
            action='PHI_ACCESS_GRANTED',
            request=request,
            phi_accessed=True,
            metadata={
                'view': view.__class__.__name__,
                'path': request.path,
            }
        )

        return True

    def has_object_permission(self, request, view, obj):
        """Log PHI object access"""
        from plane.utils.audit import create_audit_log, log_phi_access

        # Call parent
        super().has_object_permission(request, view, obj)

        resource_type = obj.__class__.__name__
        resource_id = getattr(obj, 'id', None) or getattr(obj, 'pk', None)

        # Log detailed PHI access
        log_phi_access(
            request=request,
            resource_type=resource_type,
            resource_id=resource_id,
            phi_category=self._get_phi_category(obj),
            access_reason=request.META.get('HTTP_X_ACCESS_REASON', '')
        )

        return True

    def _get_phi_category(self, obj):
        """Determine PHI category based on object type"""
        model_name = obj.__class__.__name__

        category_mapping = {
            'User': 'demographics',
            'Profile': 'contact',
            'Issue': 'case_notes',
            'IssueComment': 'case_notes',
            'Intake': 'demographics',
            'FileAsset': 'attachments',
        }

        return category_mapping.get(model_name, 'case_notes')


class SessionTimeoutPermission(HIPAABasePermission):
    """
    Permission class that enforces session inactivity timeout.

    Checks if the session has been inactive beyond the configured
    timeout period and denies access if expired.
    """

    message = 'Session has expired due to inactivity. Please log in again.'

    def has_permission(self, request, view):
        """Check session timeout"""
        # Call parent to log access attempt
        super().has_permission(request, view)

        if not request.user.is_authenticated:
            return False

        # Get timeout settings
        inactivity_timeout = getattr(
            settings, 'HIPAA_SESSION_INACTIVITY_TIMEOUT', 900
        )
        max_session_age = getattr(
            settings, 'HIPAA_SESSION_MAX_AGE', 28800
        )

        # Check last activity time
        last_activity = request.session.get('last_activity')
        session_start = request.session.get('session_start')
        current_time = timezone.now().timestamp()

        if last_activity:
            inactive_duration = current_time - last_activity
            if inactive_duration > inactivity_timeout:
                from plane.utils.audit import create_audit_log
                create_audit_log(
                    action='SESSION_TIMEOUT_INACTIVITY',
                    request=request,
                    metadata={'inactive_seconds': inactive_duration}
                )
                return False

        if session_start:
            session_duration = current_time - session_start
            if session_duration > max_session_age:
                from plane.utils.audit import create_audit_log
                create_audit_log(
                    action='SESSION_TIMEOUT_MAX_AGE',
                    request=request,
                    metadata={'session_duration': session_duration}
                )
                return False

        # Update last activity
        request.session['last_activity'] = current_time
        if not session_start:
            request.session['session_start'] = current_time

        return True


class ConcurrentSessionPermission(HIPAABasePermission):
    """
    Permission class that limits concurrent sessions per user.

    Prevents credential sharing and limits exposure from compromised
    credentials by restricting the number of active sessions.
    """

    message = 'Maximum concurrent sessions exceeded. Please log out from another device.'

    def has_permission(self, request, view):
        """Check concurrent session limit"""
        from plane.db.models import Session

        # Call parent to log access attempt
        super().has_permission(request, view)

        if not request.user.is_authenticated:
            return False

        max_sessions = getattr(settings, 'HIPAA_MAX_CONCURRENT_SESSIONS', 3)

        # Count active sessions for this user
        active_sessions = Session.objects.filter(
            user_id=request.user.id,
            is_active=True
        ).count()

        if active_sessions > max_sessions:
            from plane.utils.audit import create_audit_log
            create_audit_log(
                action='CONCURRENT_SESSION_LIMIT_EXCEEDED',
                request=request,
                metadata={
                    'active_sessions': active_sessions,
                    'max_allowed': max_sessions
                },
                severity='warning'
            )
            return False

        return True
