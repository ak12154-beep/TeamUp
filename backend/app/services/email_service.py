import smtplib
from email.message import EmailMessage

from app.core.config import settings


class EmailService:
    @staticmethod
    def send_verification_code(email: str, code: str) -> None:
        if not settings.smtp_host or not settings.smtp_from_email:
            raise RuntimeError("SMTP is not configured. Set SMTP_HOST and SMTP_FROM_EMAIL in .env")

        message = EmailMessage()
        message["Subject"] = "TeamUp verification code"
        message["From"] = settings.smtp_from_email
        message["To"] = email
        message.set_content(
            f"Your TeamUp verification code is: {code}\n"
            f"This code expires in {settings.verification_code_ttl_min} minutes."
        )

        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=20) as server:
                if settings.smtp_user and settings.smtp_password:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(message)
            return

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)
