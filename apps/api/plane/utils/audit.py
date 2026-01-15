"""
HIPAA Audit Logging Utilities

This module provides utility functions for creating audit log entries
in a consistent manner across the application.
"""

import hashlib
import uuid
import logging

from django.conf import settings

logger = logging.getLogger('plane.audit')


def get_client_ip(request):
    """Extract client IP address from request, handling proxies"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Take the first IP in the chain (original client)
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def hash_email(email):
    """Create SHA-256 hash of email for privacy-preserving logging"""
    if not email:
        return None
    return hashlib.sha256(email.lower().encode()).hexdigest()


def get_request_id(request):
    """Get or generate a unique request ID for correlation"""
    request_id = request.META.get('HTTP_X_REQUEST_ID')
    if not request_id:
        request_id = str(uuid.uuid4())
    return request_id


def create_audit_log(
    action,
    request=None,
    user=None,
    workspace_slug=None,
    workspace_id=None,
    project_id=None,
    resource_type=None,
    resource_id=None,
    metadata=None,
    phi_accessed=False,
    phi_fields=None,
    severity='info',
    changes=None,
):
    """
    Create an immutable audit log entry.

    Args:
        action: String describing the action (e.g., 'VIEW_ISSUE', 'UPDATE_USER')
        request: Django request object (optional, for extracting context)
        user: User object (optional, extracted from request if available)
        workspace_slug: Workspace slug for context
        workspace_id: Workspace UUID
        project_id: Project UUID
        resource_type: Type of resource (e.g., 'Issue', 'User')
        resource_id: UUID of the resource
        metadata: Additional data dict
        phi_accessed: Boolean indicating PHI was accessed
        phi_fields: List of PHI field names accessed
        severity: Log severity ('debug', 'info', 'warning', 'error', 'critical')
        changes: Dict with 'before' and 'after' for update operations

    Returns:
        AuditLog instance
    """
    # Check if audit logging is enabled
    if not getattr(settings, 'HIPAA_AUDIT_ENABLED', True):
        return None

    # Import here to avoid circular imports
    from plane.db.models.audit import AuditLog

    # Extract user from request if not provided
    if request and not user:
        user = getattr(request, 'user', None)
        if user and not user.is_authenticated:
            user = None

    # Build log entry data
    log_data = {
        'action': action,
        'severity': severity,
        'phi_accessed': phi_accessed,
        'phi_fields': phi_fields or [],
        'data': metadata or {},
        'changes': changes or {},
    }

    # Add user information
    if user:
        log_data['user_id'] = user.id
        log_data['user_email_hash'] = hash_email(getattr(user, 'email', None))
        log_data['actor_type'] = 'user'

    # Add request context
    if request:
        log_data['ip_address'] = get_client_ip(request)
        log_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')[:500]
        log_data['request_id'] = get_request_id(request)
        log_data['session_id'] = request.session.session_key if hasattr(request, 'session') else None

        # Extract workspace/project from URL kwargs if available
        if hasattr(request, 'parser_context'):
            kwargs = request.parser_context.get('kwargs', {})
            if not workspace_slug:
                workspace_slug = kwargs.get('slug')
            if not project_id:
                project_id = kwargs.get('project_id')

    # Add resource context
    if workspace_slug:
        log_data['workspace_slug'] = workspace_slug
    if workspace_id:
        log_data['workspace_id'] = workspace_id
    if project_id:
        log_data['project_id'] = project_id
    if resource_type:
        log_data['resource_type'] = resource_type
    if resource_id:
        log_data['resource_id'] = resource_id

    try:
        audit_log = AuditLog.objects.create(**log_data)

        # Log to standard logging as well
        log_message = f"AUDIT: {action} by user={log_data.get('user_id')} resource={resource_type}:{resource_id}"
        if phi_accessed:
            log_message += " [PHI]"

        logger.info(log_message, extra={'audit_id': str(audit_log.id)})

        return audit_log

    except Exception as e:
        # Never let audit logging failures break the application
        logger.error(f"Failed to create audit log: {e}", exc_info=True)
        return None


def log_phi_access(
    request,
    resource_type,
    resource_id,
    phi_category,
    access_reason=None,
    data_subject_id=None,
):
    """
    Log PHI access event with detailed tracking.

    This creates both a standard audit log entry and a specialized
    PHI access log for compliance reporting.

    Args:
        request: Django request object
        resource_type: Type of resource containing PHI
        resource_id: UUID of the resource
        phi_category: Category of PHI (demographics, contact, health, etc.)
        access_reason: Documented reason for accessing PHI
        data_subject_id: UUID of the person whose PHI was accessed
    """
    # Check if PHI access logging is enabled
    if not getattr(settings, 'HIPAA_PHI_ACCESS_LOGGING', True):
        return None

    from plane.db.models.audit import AuditLog, PHIAccessLog

    # Create the main audit log
    audit_log = create_audit_log(
        action='PHI_ACCESS',
        request=request,
        resource_type=resource_type,
        resource_id=resource_id,
        phi_accessed=True,
        metadata={
            'phi_category': phi_category,
            'access_reason': access_reason,
            'data_subject_id': str(data_subject_id) if data_subject_id else None,
        }
    )

    if not audit_log:
        return None

    try:
        # Create specialized PHI access log
        phi_log = PHIAccessLog.objects.create(
            audit_log=audit_log,
            phi_category=phi_category,
            access_reason=access_reason or '',
            data_subject_id=data_subject_id,
        )

        logger.info(
            f"PHI_ACCESS: {phi_category} accessed for subject={data_subject_id}",
            extra={'phi_log_id': str(phi_log.id)}
        )

        return phi_log

    except Exception as e:
        logger.error(f"Failed to create PHI access log: {e}", exc_info=True)
        return None


def log_security_event(
    event_type,
    request=None,
    user=None,
    details=None,
    severity='warning',
):
    """
    Log a security-related event.

    Args:
        event_type: Type of security event (e.g., 'FAILED_LOGIN', 'SUSPICIOUS_ACTIVITY')
        request: Django request object
        user: User object if known
        details: Additional details about the event
        severity: Event severity
    """
    from plane.utils.alerts import send_security_alert

    # Create audit log
    audit_log = create_audit_log(
        action=f'SECURITY_{event_type}',
        request=request,
        user=user,
        metadata=details or {},
        severity=severity,
    )

    # Send security alert for high-severity events
    if severity in ('error', 'critical'):
        send_security_alert(
            event_type=event_type,
            details=details,
            request=request,
        )

    return audit_log


def log_data_export(
    request,
    export_type,
    workspace_id=None,
    project_id=None,
    record_count=0,
    includes_phi=False,
):
    """
    Log a data export event for compliance tracking.

    Data exports are high-risk events and require detailed logging.
    """
    return create_audit_log(
        action='DATA_EXPORT',
        request=request,
        workspace_id=workspace_id,
        project_id=project_id,
        metadata={
            'export_type': export_type,
            'record_count': record_count,
            'includes_phi': includes_phi,
        },
        phi_accessed=includes_phi,
        severity='warning' if includes_phi else 'info',
    )


def log_bulk_operation(
    request,
    operation,
    resource_type,
    resource_ids,
    workspace_id=None,
    project_id=None,
):
    """
    Log a bulk operation for audit purposes.

    Bulk operations can affect many records and need special tracking.
    """
    return create_audit_log(
        action=f'BULK_{operation.upper()}',
        request=request,
        workspace_id=workspace_id,
        project_id=project_id,
        resource_type=resource_type,
        metadata={
            'operation': operation,
            'resource_count': len(resource_ids),
            'resource_ids': [str(rid) for rid in resource_ids[:100]],  # Limit to 100
        },
        severity='warning',
    )


def verify_audit_log_integrity(audit_log_id):
    """
    Verify the integrity of an audit log entry.

    Returns True if the checksum matches, False otherwise.
    """
    from plane.db.models.audit import AuditLog

    try:
        audit_log = AuditLog.objects.get(id=audit_log_id)
        return audit_log.verify_integrity()
    except AuditLog.DoesNotExist:
        return False


def get_phi_access_report(
    start_date,
    end_date,
    user_id=None,
    data_subject_id=None,
):
    """
    Generate a PHI access report for compliance.

    Args:
        start_date: Report start date
        end_date: Report end date
        user_id: Filter by accessing user (optional)
        data_subject_id: Filter by data subject (optional)

    Returns:
        QuerySet of PHI access logs
    """
    from plane.db.models.audit import PHIAccessLog

    queryset = PHIAccessLog.objects.filter(
        timestamp__gte=start_date,
        timestamp__lte=end_date,
    ).select_related('audit_log')

    if user_id:
        queryset = queryset.filter(audit_log__user_id=user_id)

    if data_subject_id:
        queryset = queryset.filter(data_subject_id=data_subject_id)

    return queryset.order_by('-timestamp')
