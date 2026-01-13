"""
Email service для отправки писем
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_email(
    to_email: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None
) -> bool:
    """
    Отправка email через SMTP.
    В dev режиме просто логирует письмо.
    """
    # В dev режиме или без SMTP настроек - просто логируем
    if settings.ENVIRONMENT == "development" or not settings.SMTP_HOST:
        logger.info(f"[DEV EMAIL] To: {to_email}")
        logger.info(f"[DEV EMAIL] Subject: {subject}")
        logger.info(f"[DEV EMAIL] Body: {body}")
        print(f"\n{'='*50}")
        print(f"📧 EMAIL (dev mode - not sent)")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Body: {body}")
        print(f"{'='*50}\n")
        return True
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to_email
        
        # Text part
        part1 = MIMEText(body, "plain", "utf-8")
        msg.attach(part1)
        
        # HTML part (если есть)
        if html_body:
            part2 = MIMEText(html_body, "html", "utf-8")
            msg.attach(part2)
        
        # Отправка
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())
        
        logger.info(f"Email sent to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


async def send_email_change_code(to_email: str, code: str) -> bool:
    """
    Отправка кода подтверждения смены email
    """
    subject = "Подтверждение смены email - MedTest"
    body = f"""
Здравствуйте!

Вы запросили смену email на адрес: {to_email}

Ваш код подтверждения: {code}

Код действителен 15 минут.

Если вы не запрашивали смену email, проигнорируйте это письмо.

С уважением,
MedTest Platform
"""
    
    html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #3B82F6;">Подтверждение смены email</h2>
    <p>Здравствуйте!</p>
    <p>Вы запросили смену email на адрес: <strong>{to_email}</strong></p>
    <p>Ваш код подтверждения:</p>
    <div style="background: #f3f4f6; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 8px; margin: 20px 0;">
        {code}
    </div>
    <p style="color: #6b7280;">Код действителен 15 минут.</p>
    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
    <p style="color: #9ca3af; font-size: 12px;">
        Если вы не запрашивали смену email, проигнорируйте это письмо.
    </p>
</body>
</html>
"""
    
    return await send_email(to_email, subject, body, html_body)
