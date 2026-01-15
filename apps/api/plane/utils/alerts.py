"""Security Alert System - SMS and Email

Sends security alerts via SMS (Twilio) and Email for critical
security events like:
- Break glass login attempts (success/failure)
- Session revocation
- Unauthorized access attempts
"""

import logging
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger("plane.security")


def send_security_alert(
    title: str,
    message: str,
    severity: str = "high",
    channels: list = None,
) -> dict:
    """
    Send a security alert via SMS and/or Email.

    Args:
        title: Alert title/subject
        message: Alert body/content
        severity: Alert severity level (low, medium, high, critical)
        channels: List of channels to use ["sms", "email"]. Defaults to both.

    Returns:
        dict with success status for each channel attempted
    """
    if channels is None:
        channels = ["sms", "email"]

    # Filter to allowed channels only
    allowed = {"sms", "email"}
    channels = [c for c in channels if c in allowed]

    results = {}

    if "email" in channels:
        results["email"] = _send_email_alert(title, message, severity)

    if "sms" in channels:
        results["sms"] = _send_sms_alert(title, message, severity)

    return results


def _send_email_alert(title: str, message: str, severity: str) -> bool:
    """Send security alert via email."""
    try:
        from_email = getattr(settings, "SECURITY_ALERT_FROM_EMAIL", None)
        recipient_list = getattr(settings, "SECURITY_ALERT_EMAILS", [])

        if not from_email:
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@plane.so")

        if not recipient_list:
            logger.warning("SECURITY_ALERT_EMAILS not configured, skipping email alert")
            return False

        # Ensure recipient_list is a list
        if isinstance(recipient_list, str):
            recipient_list = [email.strip() for email in recipient_list.split(",")]

        subject = f"[{severity.upper()}] {title}"

        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=False,
        )

        logger.info(f"Security alert email sent: {title}")
        return True

    except Exception as e:
        logger.error(f"Failed to send security alert email: {e}")
        return False


def _send_sms_alert(title: str, message: str, severity: str) -> bool:
    """Send security alert via SMS using Twilio."""
    try:
        account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
        auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None)
        from_number = getattr(settings, "TWILIO_PHONE_NUMBER", None)
        phone_numbers = getattr(settings, "SECURITY_ALERT_PHONES", [])

        if not all([account_sid, auth_token, from_number]):
            logger.warning("Twilio not configured, skipping SMS alert")
            return False

        if not phone_numbers:
            logger.warning("SECURITY_ALERT_PHONES not configured, skipping SMS alert")
            return False

        # Ensure phone_numbers is a list
        if isinstance(phone_numbers, str):
            phone_numbers = [phone.strip() for phone in phone_numbers.split(",")]

        try:
            from twilio.rest import Client
        except ImportError:
            logger.warning("Twilio library not installed, skipping SMS alert")
            return False

        client = Client(account_sid, auth_token)

        # Truncate message for SMS (160 char limit per segment)
        sms_body = f"[{severity.upper()}] {title}\n{message[:140]}"

        success_count = 0
        for phone in phone_numbers:
            try:
                client.messages.create(
                    body=sms_body,
                    from_=from_number,
                    to=phone,
                )
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to send SMS to {phone}: {e}")

        if success_count > 0:
            logger.info(f"Security alert SMS sent to {success_count}/{len(phone_numbers)} recipients: {title}")
            return True
        return False

    except Exception as e:
        logger.error(f"Failed to send security alert SMS: {e}")
        return False


def log_security_event(
    event_type: str,
    user_email: str = None,
    user_id: str = None,
    ip_address: str = None,
    user_agent: str = None,
    metadata: dict = None,
):
    """
    Log a security event for audit purposes.

    Args:
        event_type: Type of security event (e.g., "BREAK_GLASS_LOGIN", "SESSION_REVOKED")
        user_email: Email of the user involved
        user_id: ID of the user involved
        ip_address: IP address of the request
        user_agent: User agent string
        metadata: Additional metadata to log
    """
    extra = {
        "event_type": event_type,
        "user_email": user_email,
        "user_id": user_id,
        "ip_address": ip_address,
        "user_agent": user_agent,
    }

    if metadata:
        extra.update(metadata)

    logger.info(f"Security event: {event_type}", extra=extra)
