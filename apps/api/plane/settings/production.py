"""Production settings"""

import os

from .common import *  # noqa

# Import HIPAA compliance settings
from .hipaa import *  # noqa

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = int(os.environ.get("DEBUG", 0)) == 1

# =============================================================================
# HIPAA SECURITY SETTINGS
# =============================================================================

# Force HTTPS - disabled since nginx handles SSL termination
SECURE_SSL_REDIRECT = False

# Honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# HTTP Strict Transport Security (HSTS) - handled by nginx
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Secure cookies
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# Content Security Policy headers
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Referrer Policy
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# =============================================================================
# SESSION SETTINGS (HIPAA Compliant)
# =============================================================================

# 15-minute inactivity timeout
SESSION_COOKIE_AGE = int(os.environ.get('HIPAA_SESSION_INACTIVITY_TIMEOUT', 900))

# Session expires when browser closes
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Update session on every request (for activity tracking)
SESSION_SAVE_EVERY_REQUEST = True

INSTALLED_APPS += ("scout_apm.django",)  # noqa


# Scout Settings
SCOUT_MONITOR = os.environ.get("SCOUT_MONITOR", False)
SCOUT_KEY = os.environ.get("SCOUT_KEY", "")
SCOUT_NAME = "Plane"

LOG_DIR = os.path.join(BASE_DIR, "logs")  # noqa

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "verbose": {"format": "%(asctime)s [%(process)d] %(levelname)s %(name)s: %(message)s"},
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "fmt": "%(levelname)s %(asctime)s %(module)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "level": "INFO",
        },
        "file": {
            "class": "plane.utils.logging.SizedTimedRotatingFileHandler",
            "filename": (
                os.path.join(BASE_DIR, "logs", "plane-debug.log")  # noqa
                if DEBUG
                else os.path.join(BASE_DIR, "logs", "plane-error.log")  # noqa
            ),
            "when": "s",
            "maxBytes": 1024 * 1024 * 1,
            "interval": 1,
            "backupCount": 5,
            "formatter": "json",
            "level": "DEBUG" if DEBUG else "ERROR",
        },
    },
    "loggers": {
        "plane.api.request": {
            "level": "DEBUG" if DEBUG else "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "plane.api": {
            "level": "DEBUG" if DEBUG else "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "plane.worker": {
            "level": "DEBUG" if DEBUG else "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "plane.exception": {
            "level": "DEBUG" if DEBUG else "ERROR",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "plane.external": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "plane.mongo": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "plane.migrations": {
            "level": "DEBUG" if DEBUG else "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        # HIPAA Audit Logging
        "plane.audit": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "plane.retention": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        },
    },
}
