from celery import Celery
import smtplib
from email.mime.text import MIMEText
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker
from src.config import config
from src.redis_client import redis_client
from src.models.VideoModel import Video
from src.models.UserModel import User
from src.models.CommentModel import Comment

# ---------- DB ----------
engine = create_engine(config.env_data.DB_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)

# ---------- Celery ----------
celery_app = Celery(
    "video_hosting",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0",
)

celery_app.conf.timezone = "UTC"

# ---------- Beat ----------
celery_app.conf.beat_schedule = {
    "sync-video-views-every-minute": {
        "task": "sync_views",
        "schedule": 60.0,
    },
}

# ---------- Email ----------
@celery_app.task(name="send_email")
def send_email(to_email: str, subject: str, message: str):
    msg = MIMEText(message, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = config.env_data.SMTP_USER
    msg["To"] = to_email

    with smtplib.SMTP(
        config.env_data.SMTP_HOST,
        config.env_data.SMTP_PORT,
        timeout=10,
    ) as server:
        server.starttls()
        server.login(
            config.env_data.SMTP_USER,
            config.env_data.SMTP_PASSWORD,
        )
        server.send_message(msg)

# ---------- Task ----------
@celery_app.task(
    name="sync_views",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=10,
)
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
