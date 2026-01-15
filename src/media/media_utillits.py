from typing import Generator
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.db import get_session
from src.get_current_user import get_current_user
from src.models.VideoModel import Video, VideoLike
from src.models.UserModel import User

# Генератор чанков файла
def file_iterator(
    file_path: str,
    start: int,
    end: int,
    chunk_size: int = 1024 * 1024
) -> Generator[bytes, None, None]:
    with open(file_path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1

        while remaining > 0:
            read_size = min(chunk_size, remaining)
            data = f.read(read_size)
            if not data:
                break
            remaining -= len(data)
            yield data

# Функция для проверки наличия видео в БД
async def get_video_or_404(
    video_id: int,
    session: AsyncSession = Depends(get_session),
) -> Video:
    video = await session.scalar(
        select(Video).where(Video.id == video_id)
    )

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    return video

# Проверка владельца видео
async def get_video_owned_by_user(
    video: Video = Depends(get_video_or_404),
    user: User = Depends(get_current_user),
) -> Video:
    if video.author_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to modify this video",
        )

    return video

# Лайки
async def get_user_video_like(
    video: Video = Depends(get_video_or_404),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> VideoLike | None:
    return await session.scalar(
        select(VideoLike).where(
            VideoLike.video_id == video.id,
            VideoLike.user_id == user.id,
        )
    )