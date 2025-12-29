import os
import pathlib
import uuid
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from src.db import get_session
from src.media.media_utillits import file_iterator
from src.get_current_user import get_current_user
from src.models.UserModel import User
from src.models.VideoModel import Video, VideoLike
from src.models.CommentModel import Comment
from src.media.media_shema import VideoShow





app = APIRouter(prefix="/media", tags=["Media"])
UPLOAD_DIR = pathlib.Path("videos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# Загрузка видео
@app.post("/upload")
async def upload_video(
    title: str = Form(...),
    file: UploadFile = File(...),
    description: str = Form(...),
    user: User = Depends(get_current_user),
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

        video = Video(title=title, 
                      description=description, 
                      url=f"/media/video/{new_name}", 
                      author_id=user.id)

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
        "url": video.url
    }

# Стриминг видео
@app.get("/media/video/{video_id}")
async def stream_video(
    video_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    # 1. Получаем видео
    video = await session.scalar(
        select(Video).where(Video.id == video_id)
    )

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    file_path = UPLOAD_DIR / pathlib.Path(video.url).name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("range")

    # 2. Счётчик просмотров  
    await session.execute(
    update(Video)
    .where(Video.id == video_id)
    .values(views=Video.views + 1)
    )
    await session.commit()

    # 3. Если Range отсутствует — отдаём всё
    if not range_header:
        return StreamingResponse(
            file_iterator(str(file_path), 0, file_size - 1),
            media_type="video/mp4",
            headers={
                "Content-Length": str(file_size),
                "Accept-Ranges": "bytes",
            },
        )

    # 4. Парсинг Range
    try:
        _, range_value = range_header.split("=")
        start_str, end_str = range_value.split("-")
        start = int(start_str)
        end = int(end_str) if end_str else file_size - 1
    except Exception:
        raise HTTPException(status_code=416, detail="Invalid Range header")

    if start >= file_size:
        raise HTTPException(status_code=416, detail="Range not satisfiable")

    end = min(end, file_size - 1)
    content_length = end - start + 1

    # 5. Частичный ответ
    return StreamingResponse(
        file_iterator(str(file_path), start, end),
        status_code=206,
        media_type="video/mp4",
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
        },
    )


# Получение информации о видео
@app.get("/desc/{video_id}", response_model=VideoShow)
async def get_video(
    video_id: int,
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Video).where(Video.id==video_id).options(selectinload(Video.author))
    video = await session.scalar(stmt)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    return video

# Удаление видео по id
@app.delete("/video/{video_id}", status_code=204)
async def delete_video(
    video_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Video).where(Video.id == video_id)
    )
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Проверка владельца
    if video.author_id != user.id:
        raise HTTPException(status_code=403, detail="You are not allowed to delete this video")

    file_path = UPLOAD_DIR / pathlib.Path(video.url).name

    try:
        # Удаляем запись из БД
        await session.delete(video)
        await session.commit()

        # Удаляем файл (если существует)
        if file_path.exists():
            file_path.unlink()

    except Exception:
        await session.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete video")

    return None

# Ставим like
@app.post("/video/{video_id}/like")
async def toggle_like(
    video_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # Проверяем, есть ли видео
    video_exists = await session.scalar(
        select(Video.id).where(Video.id == video_id)
    )
    if not video_exists:
        raise HTTPException(status_code=404, detail="Video not found")

    # Проверяем, есть ли лайк
    like = await session.scalar(
        select(VideoLike)
        .where(
            VideoLike.video_id == video_id,
            VideoLike.user_id == user.id,
        )
    )

    # Лайк уже есть - снимаем
    if like:
        await session.execute(
            delete(VideoLike)
            .where(VideoLike.id == like.id)
        )
        await session.execute(
            update(Video)
            .where(Video.id == video_id)
            .values(likes=Video.likes - 1)
        )
        await session.commit()

        return {"liked": False}

    # Лайка нет - ставим
    session.add(
        VideoLike(user_id=user.id, video_id=video_id)
    )
    await session.execute(
        update(Video)
        .where(Video.id == video_id)
        .values(likes=Video.likes + 1)
    )
    await session.commit()

    return {"liked": True}

# Получить статус лайка для пользователя
@app.get("/video/{video_id}/like")
async def is_liked(
    video_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    liked = await session.scalar(
        select(VideoLike.id)
        .where(
            VideoLike.video_id == video_id,
            VideoLike.user_id == user.id,
        )
    )
    return {"liked": bool(liked)}