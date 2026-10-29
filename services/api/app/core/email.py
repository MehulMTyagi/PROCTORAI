import smtplib
from email.message import EmailMessage

from app.core.config import settings


def send_verification_code(email: str, code: str) -> None:
    if not settings.smtp_host or not settings.smtp_from_email:
        raise RuntimeError("Email delivery is not configured")

    message = EmailMessage()
    message["Subject"] = "Verify your ProctorAI student account"
    message["From"] = settings.smtp_from_email
    message["To"] = email
    message.set_content(
        f"Your ProctorAI verification code is {code}. It expires in 15 minutes. "
        "If you did not create this account, you can ignore this email."
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
        server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password or "")
        server.send_message(message)
