from celery import Celery
from fastapi import HTTPException
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.config import config

celery_app = Celery(
    "animal_app",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0",
)

celery_app.autodiscover_tasks(["src.tasks"])


host = config.env_data.SMTP_HOST
port = config.env_data.SMTP_PORT
user = config.env_data.SMTP_USER
password = config.env_data.SMTP_PASSWORD


@celery_app.task()
def send_email(to_email:str, subject: str, message: str):
    msg = MIMEText(message, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = config.env_data.SMTP_USER
    msg["To"] = to_email
        
    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        print("Email отправлен успешно")
    except Exception as e:
        raise HTTPException(500, f"Email send failed: {e}")