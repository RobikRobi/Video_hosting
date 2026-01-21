import os
import pathlib
import uuid
import aiofiles
# import dropbox
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, func, select
from sqlalchemy.orm import selectinload
from src.db import get_session
from src.media.media_utillits import file_iterator, get_video_or_404, get_video_owned_by_user
from src.media.media_utillits import get_user_video_like, get_user_channel, get_comment_or_404
from src.media.media_utillits import check_comment_owner
from src.get_current_user import get_current_user
from src.models.UserModel import User
from src.models.VideoModel import Video, VideoLike
from src.models.CommentModel import Comment
from src.models.ChannelModel import Channel
from src.media.media_shema import VideoShow, CommentCreate, CommentOut, CommentUpdate



app = APIRouter(prefix="/media", tags=["Media"])

# app = APIRouter(prefix="/videos", tags=["Videos"])
# dbx = dropbox.Dropbox(config.env_data.ACCESS_TOKEN)
UPLOAD_DIR = pathlib.Path("videos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# Загрузка видео
@app.post("/upload")
async def upload_video(
    title: str = Form(...),
    description: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    channel: Channel = Depends(get_user_channel),
    session: AsyncSession = Depends(get_session),
):
    ext = pathlib.Path(file.filename).suffix.lower()
    if ext != ".mp4":
        raise HTTPException(status_code=400, detail="Only MP4 files are allowed")

    new_name = f"{uuid.uuid4()}{ext}"
    dist = UPLOAD_DIR / new_name

    try:
        async with aiofiles.open(dist, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                await f.write(chunk)

        video = Video(
            title=title,
            description=description,
            url=f"/video/{new_name}",
            author_id=user.id,
            channel_id=channel.id, 
        )

        session.add(video)
        await session.commit()
        await session.refresh(video)

    except Exception:
        await session.rollback()
        if dist.exists():
            dist.unlink()
        raise

    finally:
        await file.close()

    return {
        "id": video.id,
        "status": "saved",
        "filename": new_name,
        "url": video.url,
        "channel_id": channel.id,
    }


# Стриминг видео
@app.get("/video/{video_id}")
async def stream_video(
    request: Request,
    video: Video = Depends(get_video_or_404),
    session: AsyncSession = Depends(get_session),
):
    # 1. Проверяем наличие файла
    file_path = UPLOAD_DIR / pathlib.Path(video.url).name

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video file not found",
        )

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("range")

    # 2. Инкремент просмотров (без race condition)
    await session.execute(
        update(Video)
        .where(Video.id == video.id)
        .values(views=func.coalesce(Video.views, 0) + 1)
    )
    await session.commit()

    # 3. Если Range нет — отдаём весь файл
    if not range_header:
        return StreamingResponse(
            file_iterator(str(file_path), 0, file_size - 1),
            media_type="video/mp4",
            headers={
                "Content-Length": str(file_size),
                "Accept-Ranges": "bytes",
            },
        )

    # 4. Парсим Range
    try:
        _, range_value = range_header.split("=")
        start_str, end_str = range_value.split("-")
        start = int(start_str)
        end = int(end_str) if end_str else file_size - 1
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail="Invalid Range header",
        )

    if start >= file_size:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail="Range not satisfiable",
        )

    end = min(end, file_size - 1)
    content_length = end - start + 1

    # 5. Частичный контент
    return StreamingResponse(
        file_iterator(str(file_path), start, end),
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        media_type="video/mp4",
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
        },
    )

# Получение информации о видео
@app.get("/info/{video_id}", response_model=VideoShow)
async def get_video(video: Video = Depends(get_video_or_404)):
    return video

# Удаление видео по id
@app.delete("/video/{video_id}", status_code=204)
async def delete_video(
    video: Video = Depends(get_video_owned_by_user),
    session: AsyncSession = Depends(get_session),
):
    file_path = UPLOAD_DIR / pathlib.Path(video.url).name

    try:
        await session.delete(video)
        await session.commit()

        if file_path.exists():
            file_path.unlink()

    except Exception:
        await session.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete video")

    return None

# Ставим like
@app.post("/video/{video_id}/like")
async def toggle_like(
    video: Video = Depends(get_video_or_404),
    like: VideoLike | None = Depends(get_user_video_like),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if like:
        # снимаем лайк
        await session.delete(like)
        await session.execute(
            update(Video)
            .where(Video.id == video.id)
            .values(likes=Video.likes - 1)
        )
        await session.commit()
        return {"liked": False}

    # ставим лайк
    session.add(
        VideoLike(user_id=user.id, video_id=video.id)
    )
    await session.execute(
        update(Video)
        .where(Video.id == video.id)
        .values(likes=Video.likes + 1)
    )
    await session.commit()

    return {"liked": True}

# Получить статус лайка для пользователя
@app.get("/video/{video_id}/like")
async def is_liked(
    like: VideoLike | None = Depends(get_user_video_like),
):
    return {"liked": like is not None}

# Оставить комментарии под видео
@app.post("/{video_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def create_comment(
    data: CommentCreate,
    video: Video = Depends(get_video_or_404),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    comment = Comment(
        text=data.text,
        user_id=user.id,
        video_id=video.id,
    )

    session.add(comment)
    await session.commit()
    await session.refresh(comment)

    return comment

# Получение всех комментариев под видео
@app.get(
    "/{video_id}/comments",
    response_model=list[CommentOut],
    status_code=status.HTTP_200_OK
)
async def get_video_comments(
    video: Video = Depends(get_video_or_404),
    session: AsyncSession = Depends(get_session)
):
    stmt = (
        select(Comment)
        .where(Comment.video_id == video.id)
        .options(
            selectinload(Comment.user)  # автор комментария
        )
        .order_by(Comment.created_at.asc())
    )

    result = await session.scalars(stmt)
    comments = result.all()

    return comments

# Получение комментария по id
@app.get("/comments/{comment_id}", response_model=CommentOut)
async def get_comment(
    comment: Comment = Depends(get_comment_or_404),
    session: AsyncSession = Depends(get_session)
):
    return comment


# Редактировать комментарий к видео
@app.patch("/comments/{comment_id}", response_model=CommentOut)
async def update_comment(
    data: CommentUpdate,
    comment: Comment = Depends(check_comment_owner),
    session: AsyncSession = Depends(get_session)
):
    comment.text = data.text

    await session.commit()
    await session.refresh(comment)

    return comment

# Удаление комментария
@app.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment: Comment = Depends(check_comment_owner),
    session: AsyncSession = Depends(get_session),
):
    await session.delete(comment)
    await session.commit()