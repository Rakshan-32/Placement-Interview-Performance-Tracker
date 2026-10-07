import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


def _get_smtp_config():
    password = os.environ.get("SMTP_PASSWORD", "")
    if password:
        password = password.replace(" ", "")
    return {
        "host": os.environ.get("SMTP_HOST", ""),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "username": os.environ.get("SMTP_USERNAME", ""),
        "password": password,
        "from_addr": os.environ.get("SMTP_FROM", ""),
        "use_tls": os.environ.get("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes"),
    }


APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://127.0.0.1:8000")


def _smtp_configured() -> bool:
    cfg = _get_smtp_config()
    return bool(cfg["host"] and cfg["username"] and cfg["password"] and cfg["from_addr"])


def _send_email(to_email: str, subject: str, html_body: str) -> dict:
    if not _smtp_configured():
        logger.info("Email delivery mode: development fallback (SMTP not configured). To: %s", to_email)
        return {"sent": False, "delivery_mode": "development", "reason": "SMTP not configured"}

    cfg = _get_smtp_config()
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = cfg["from_addr"]
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as server:
            server.ehlo()
            if cfg["use_tls"]:
                server.starttls()
                server.ehlo()
            server.login(cfg["username"], cfg["password"])
            server.sendmail(cfg["from_addr"], [to_email], msg.as_string())

        logger.info("Email delivery mode: SMTP. Email delivered to %s", to_email)
        return {"sent": True, "delivery_mode": "smtp"}
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed for host %s — check SMTP_USERNAME and SMTP_PASSWORD", cfg["host"])
        return {"sent": False, "delivery_mode": "smtp", "reason": "SMTP authentication failed"}
    except smtplib.SMTPException as exc:
        logger.error("SMTP error sending to %s: %s", to_email, type(exc).__name__)
        return {"sent": False, "delivery_mode": "smtp", "reason": f"SMTP error: {type(exc).__name__}"}
    except Exception as exc:
        logger.error("Email delivery failed to %s: %s", to_email, type(exc).__name__)
        return {"sent": False, "delivery_mode": "smtp", "reason": "Email delivery failed"}


def send_invitation_email(to_email: str, role: str, activation_url: str, expires_in: str = "48 hours") -> dict:
    subject = "Placement Portal — You've Been Invited"
    html = f"""<div style="font-family:sans-serif;max-width:520px;margin:auto;padding:24px;background:#0f172a;color:#f8fafc;border-radius:12px;">
  <h2 style="color:#60a5fa;">Placement Portal — Account Invitation</h2>
  <p>You've been invited to the <strong>Placement Interview Performance Tracker</strong>.</p>
  <p><strong>Email:</strong> {to_email}</p>
  <p><strong>Role:</strong> {role}</p>
  <p>Activate your account and create your password:</p>
  <p style="margin:20px 0;">
    <a href="{activation_url}" style="display:inline-block;padding:12px 28px;background:#2563eb;color:#fff;border-radius:8px;text-decoration:none;font-weight:600;">
      Activate Account
    </a>
  </p>
  <p style="color:#94a3b8;font-size:0.9em;">This invitation expires in {expires_in}.</p>
  <p style="color:#64748b;font-size:0.85em;margin-top:16px;">If you did not expect this invitation, you can safely ignore this email.</p>
</div>"""
    return _send_email(to_email, subject, html)


def send_password_reset_email(to_email: str, reset_url: str, expires_in: str = "1 hour") -> dict:
    subject = "Placement Portal — Password Reset"
    html = f"""<div style="font-family:sans-serif;max-width:520px;margin:auto;padding:24px;background:#0f172a;color:#f8fafc;border-radius:12px;">
  <h2 style="color:#60a5fa;">Password Reset Request</h2>
  <p>A password reset was requested for your <strong>Placement Portal</strong> account.</p>
  <p><strong>Email:</strong> {to_email}</p>
  <p>Reset your password using the link below:</p>
  <p style="margin:20px 0;">
    <a href="{reset_url}" style="display:inline-block;padding:12px 28px;background:#2563eb;color:#fff;border-radius:8px;text-decoration:none;font-weight:600;">
      Reset Password
    </a>
  </p>
  <p style="color:#94a3b8;font-size:0.9em;">This link expires in {expires_in}.</p>
  <p style="color:#64748b;font-size:0.85em;margin-top:16px;">If you did not request a password reset, you can safely ignore this email.</p>
</div>"""
    return _send_email(to_email, subject, html)
