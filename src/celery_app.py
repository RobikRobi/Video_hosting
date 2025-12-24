from celery import Celery
import smtplib
from email.mime.text import MIMEText
from celery import shared_task
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker
from src.config import config
from src.redis_client import redis_client
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.VideoModel import Video
from sqlalchemy import update


engine = create_engine(url = config.env_data.DB_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)



celery_app = Celery(
    "app",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0",
)

celery_app.autodiscover_tasks(["src.tasks"])


celery_app.conf.beat_schedule = {
    "sync-video-views-every-minute": {
        "task": "src.tasks.sync_views.sync_views",
        "schedule": 60.0,  # раз в минуту
    },
}

celery_app.conf.timezone = "UTC"

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
        
    with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=10)
def sync_views(self):
    session = SessionLocal()
    try:
        keys = redis_client.keys("video:views:*")

        for key in keys:
            video_id = int(key.split(":")[-1])
            views = int(redis_client.get(key))

            session.execute(
                update(Video)
                .where(Video.id == video_id)
                .values(views=Video.views + views)
            )

            redis_client.delete(key)

        session.commit()

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
