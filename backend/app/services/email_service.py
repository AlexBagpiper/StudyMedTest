"""
Email service для отправки писем
"""

import logging
import smtplib
import json
from datetime import datetime
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
        # #region agent log
        with open(r'e:\pythonProject\StudyMedTest\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({'sessionId':'debug-session','runId':'run1','hypothesisId':'B','location':'email_service.py:40','message':'Attempting SMTP connection','data':{'host':settings.SMTP_HOST,'port':settings.SMTP_PORT,'timeout':10},'timestamp':datetime.utcnow().timestamp()}) + '\n')
        # #endregion
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
        smtp_class = smtplib.SMTP_SSL if settings.SMTP_PORT == 465 else smtplib.SMTP
        # #region agent log
        with open(r'e:\pythonProject\StudyMedTest\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({'sessionId':'debug-session','runId':'run1','hypothesisId':'C','location':'email_service.py:60','message':'Connecting using smtp_class','data':{'class':smtp_class.__name__},'timestamp':datetime.utcnow().timestamp()}) + '\n')
        # #endregion
        with smtp_class(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            # #region agent log
            with open(r'e:\pythonProject\StudyMedTest\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({'sessionId':'debug-session','runId':'run1','hypothesisId':'C','location':'email_service.py:64','message':'Connected successfully','timestamp':datetime.utcnow().timestamp()}) + '\n')
            # #endregion
            if settings.SMTP_PORT != 465:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                # #region agent log
                with open(r'e:\pythonProject\StudyMedTest\.cursor\debug.log', 'a') as f:
                    f.write(json.dumps({'sessionId':'debug-session','runId':'run1','hypothesisId':'B','location':'email_service.py:69','message':'Attempting login','data':{'user':settings.SMTP_USER},'timestamp':datetime.utcnow().timestamp()}) + '\n')
                # #endregion
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())
        
        # #region agent log
        with open(r'e:\pythonProject\StudyMedTest\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({'sessionId':'debug-session','runId':'run1','hypothesisId':'ALL','location':'email_service.py:76','message':'Email sent successfully','timestamp':datetime.utcnow().timestamp()}) + '\n')
        # #endregion
        logger.info(f"Email sent to {to_email}")
        return True
        
    except Exception as e:
        # #region agent log
        with open(r'e:\pythonProject\StudyMedTest\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({'sessionId':'debug-session','runId':'run1','hypothesisId':'ALL','location':'email_service.py:81','message':'SMTP Error','data':{'error':str(e)},'timestamp':datetime.utcnow().timestamp()}) + '\n')
        # #endregion
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


async def send_email_change_code(to_email: str, code: str) -> bool:
    """
    Отправка кода подтверждения смены email
    """
    subject = f"Подтверждение смены email - {settings.PROJECT_NAME}"
    body = f"""
Здравствуйте!

Вы запросили смену email на адрес: {to_email}

Ваш код подтверждения: {code}

Код действителен 15 минут.

Если вы не запрашивали смену email, проигнорируйте это письмо.

С уважением,
{settings.PROJECT_NAME}
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


async def send_verification_email(to_email: str, code: str) -> bool:
    """
    Отправка кода подтверждения регистрации
    """
    subject = f"Подтверждение регистрации - {settings.PROJECT_NAME}"
    body = f"""
Здравствуйте!

Добро пожаловать в {settings.PROJECT_NAME}.

Для завершения регистрации, пожалуйста, используйте следующий код подтверждения:

{code}

Код действителен 24 часа.

Если вы не регистрировались на нашем сервисе, просто проигнорируйте это письмо.

С уважением,
Команда {settings.PROJECT_NAME}
"""
    
    html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #374151;">
    <div style="text-align: center; padding: 20px 0;">
        <h1 style="color: #3B82F6; margin: 0;">{settings.PROJECT_NAME}</h1>
    </div>
    <div style="background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 40px; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);">
        <h2 style="margin-top: 0; color: #111827;">Подтверждение почты</h2>
        <p>Здравствуйте!</p>
        <p>Спасибо за регистрацию в <strong>{settings.PROJECT_NAME}</strong>. Для подтверждения вашего email адреса используйте код ниже:</p>
        
        <div style="background: #f3f4f6; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 8px; margin: 30px 0; color: #111827; border-radius: 4px;">
            {code}
        </div>
        
        <p style="color: #6b7280; font-size: 14px;">Код действителен в течение 24 часов.</p>
        <p>Введите этот код на странице подтверждения в приложении.</p>
        
        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
        
        <p style="color: #9ca3af; font-size: 12px; margin-bottom: 0;">
            Если вы не создавали аккаунт, просто проигнорируйте это письмо.
        </p>
    </div>
    <div style="text-align: center; padding: 20px; color: #9ca3af; font-size: 12px;">
        © {datetime.utcnow().year} {settings.PROJECT_NAME}. Все права защищены.
    </div>
</body>
</html>
"""
    
    return await send_email(to_email, subject, body, html_body)
