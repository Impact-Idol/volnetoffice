"""
HIPAA Compliance Settings

This module contains Django settings required for HIPAA compliance,
including session management, encryption, and security configurations.
"""

import os
from cryptography.fernet import Fernet

# =============================================================================
# SESSION MANAGEMENT (HIPAA §164.312(d))
# =============================================================================

# 15-minute inactivity timeout (900 seconds)
# HIPAA requires automatic logoff after period of inactivity
HIPAA_SESSION_INACTIVITY_TIMEOUT = int(os.environ.get(
    'HIPAA_SESSION_INACTIVITY_TIMEOUT', 900
))

# Session expires when browser closes
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Update session on every request to track activity
SESSION_SAVE_EVERY_REQUEST = True

# Maximum session duration regardless of activity (8 hours = 28800 seconds)
HIPAA_SESSION_MAX_AGE = int(os.environ.get(
    'HIPAA_SESSION_MAX_AGE', 28800
))

# Maximum concurrent sessions per user
# Prevents credential sharing and limits exposure
HIPAA_MAX_CONCURRENT_SESSIONS = int(os.environ.get(
    'HIPAA_MAX_CONCURRENT_SESSIONS', 3
))

# Session cookie age (use inactivity timeout for HIPAA compliance)
SESSION_COOKIE_AGE = HIPAA_SESSION_INACTIVITY_TIMEOUT


# =============================================================================
# ENCRYPTION SETTINGS (HIPAA §164.312(a)(2)(iv))
# =============================================================================

# Encryption key for field-level encryption
# MUST be set in production - generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')

# If no key is provided, generate one (only for development)
if not ENCRYPTION_KEY:
    import warnings
    warnings.warn(
        "ENCRYPTION_KEY not set. Using auto-generated key. "
        "This is only acceptable for development. "
        "Set ENCRYPTION_KEY environment variable in production.",
        RuntimeWarning
    )
    ENCRYPTION_KEY = Fernet.generate_key()


# =============================================================================
# AUDIT LOGGING (HIPAA §164.312(b))
# =============================================================================

# Enable comprehensive audit logging
HIPAA_AUDIT_ENABLED = os.environ.get('HIPAA_AUDIT_ENABLED', '1') == '1'

# Log PHI access events separately
HIPAA_PHI_ACCESS_LOGGING = os.environ.get('HIPAA_PHI_ACCESS_LOGGING', '1') == '1'

# Audit log retention period (days) - audit logs have longer retention
HIPAA_AUDIT_LOG_RETENTION_DAYS = int(os.environ.get(
    'HIPAA_AUDIT_LOG_RETENTION_DAYS', 2555  # 7 years
))


# =============================================================================
# DATA RETENTION (HIPAA §164.530(j))
# =============================================================================

# Maximum retention period in days (7 years)
HIPAA_MAX_RETENTION_DAYS = 2555

# Default retention period for different data types (in days)
HIPAA_DEFAULT_RETENTION = {
    'attachment': 2555,      # 7 years
    'issue': 2555,           # 7 years
    'issue_comment': 2555,   # 7 years
    'audit_log': 2555,       # 7 years (minimum per HIPAA)
    'user': 2555,            # 7 years
    'notification': 365,     # 1 year
    'session': 90,           # 90 days
    'api_log': 365,          # 1 year
}


# =============================================================================
# ACCESS CONTROL (HIPAA §164.312(a)(1))
# =============================================================================

# Require MFA for PHI access
HIPAA_REQUIRE_MFA_FOR_PHI = os.environ.get('HIPAA_REQUIRE_MFA_FOR_PHI', '1') == '1'

# MFA session validity period (seconds) - re-verify after this period
HIPAA_MFA_SESSION_VALIDITY = int(os.environ.get(
    'HIPAA_MFA_SESSION_VALIDITY', 3600  # 1 hour
))

# Failed login lockout threshold
HIPAA_FAILED_LOGIN_THRESHOLD = int(os.environ.get(
    'HIPAA_FAILED_LOGIN_THRESHOLD', 5
))

# Failed login lockout duration (seconds)
HIPAA_FAILED_LOGIN_LOCKOUT = int(os.environ.get(
    'HIPAA_FAILED_LOGIN_LOCKOUT', 900  # 15 minutes
))


# =============================================================================
# PASSWORD POLICY (HIPAA §164.308(a)(5)(ii)(D))
# =============================================================================

# Minimum password length
HIPAA_PASSWORD_MIN_LENGTH = int(os.environ.get(
    'HIPAA_PASSWORD_MIN_LENGTH', 12
))

# Password expiration (days) - 0 to disable
HIPAA_PASSWORD_EXPIRATION_DAYS = int(os.environ.get(
    'HIPAA_PASSWORD_EXPIRATION_DAYS', 90
))

# Password history (prevent reuse of N previous passwords)
HIPAA_PASSWORD_HISTORY_COUNT = int(os.environ.get(
    'HIPAA_PASSWORD_HISTORY_COUNT', 12
))


# =============================================================================
# TRANSMISSION SECURITY (HIPAA §164.312(e)(1))
# =============================================================================

# Force HTTPS
SECURE_SSL_REDIRECT = True

# HSTS settings
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Secure cookies
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

# Proxy SSL header (for load balancers)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# =============================================================================
# PHI FIELD DEFINITIONS
# =============================================================================

# Fields that contain PHI and require special handling
HIPAA_PHI_FIELDS = {
    'User': [
        'email',
        'first_name',
        'last_name',
        'phone_number',
        'date_of_birth',
        'address',
    ],
    'Issue': [
        'description_stripped',
        'name',  # May contain PHI in support tickets
    ],
    'IssueComment': [
        'comment_stripped',
    ],
    'Intake': [
        'name',
        'description',
        'email',
        'phone',
    ],
}


# =============================================================================
# SECURITY ALERTS
# =============================================================================

# Enable security alerts for suspicious activity
HIPAA_SECURITY_ALERTS_ENABLED = os.environ.get(
    'HIPAA_SECURITY_ALERTS_ENABLED', '1'
) == '1'

# Email recipients for security alerts
HIPAA_SECURITY_ALERT_EMAILS = os.environ.get(
    'HIPAA_SECURITY_ALERT_EMAILS', ''
).split(',')

# SMS recipients for critical security alerts
HIPAA_SECURITY_ALERT_PHONES = os.environ.get(
    'HIPAA_SECURITY_ALERT_PHONES', ''
).split(',')


# =============================================================================
# COMPLIANCE REPORTING
# =============================================================================

# Generate compliance reports automatically
HIPAA_AUTO_COMPLIANCE_REPORTS = os.environ.get(
    'HIPAA_AUTO_COMPLIANCE_REPORTS', '1'
) == '1'

# Compliance report email recipients
HIPAA_COMPLIANCE_REPORT_EMAILS = os.environ.get(
    'HIPAA_COMPLIANCE_REPORT_EMAILS', ''
).split(',')
