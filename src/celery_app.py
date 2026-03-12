import smtplib
import pathlib
import dropbox
from celery import Celery
from celery import shared_task
from dropbox.files import WriteMode
from email.mime.text import MIMEText
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import config
from src.models.UserModel import User, PasswordResetToken
from src.models.ChannelModel import Channel, Subscriptions
from src.models.VideoModel import Video, VideoLike

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

# ------------------------Save Video-------------------------
@celery_app.task(name="upload_video_task")
def upload_video_task(video_id: str, file_path: str, dropbox_path: str):

    dbx = dropbox.Dropbox(
        oauth2_refresh_token=config.env_data.DROPBOX_REFRESH_TOKEN,
        app_key=config.env_data.DROPBOX_APP_KEY,
        app_secret=config.env_data.DROPBOX_APP_SECRET,
    )

    CHUNK_SIZE = 4 * 1024 * 1024

    with open(file_path, "rb") as f:
        first_chunk = f.read(CHUNK_SIZE)

        session = dbx.files_upload_session_start(first_chunk)
        cursor = dropbox.files.UploadSessionCursor(
            session_id=session.session_id,
            offset=len(first_chunk),
        )

        while chunk := f.read(CHUNK_SIZE):
            dbx.files_upload_session_append_v2(chunk, cursor)
            cursor.offset += len(chunk)

        commit = dropbox.files.CommitInfo(
            path=dropbox_path,
            mode=WriteMode.overwrite
        )

        dbx.files_upload_session_finish(b"", cursor, commit)

    shared = dbx.sharing_create_shared_link_with_settings(dropbox_path)
    url = shared.url.replace("?dl=0", "?raw=1")

# ---------- DB ----------
    db = SessionLocal()
    try:
        video = db.get(Video, video_id)
        video.url = url
        video.status = "ready"
        db.commit()
    except Exception:
        video.status = "failed"
        db.commit()
    finally:
        db.close()
    pathlib.Path(file_path).unlink()