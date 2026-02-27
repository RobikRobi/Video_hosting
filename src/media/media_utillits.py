import numpy as np
from uuid import UUID
from typing import Generator
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.db import get_session
from src.get_current_user import get_current_user
from src.models.VideoModel import Video, VideoLike
from src.models.UserModel import User
from src.models.ChannelModel import Channel
from src.models.CommentModel import Comment




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
    video_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> Video:
    video = await session.scalar(
        select(Video)
        .where(Video.id == video_id)
        .options(
            selectinload(Video.author), 
            selectinload(Video.channel),
        )
    )

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

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

# Получение канала пользователя
async def get_user_channel(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Channel:
    channel = await session.scalar(
        select(Channel).where(Channel.owner_id == user.id)
    )

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no channel"
        )

    return channel

# Проверка наличия комментария
async def get_comment_or_404(
    comment_id: int,
    session: AsyncSession = Depends(get_session)
) -> Comment:
    comment = await session.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment

# Проверка владельца комментария
def check_comment_owner(
    comment: Comment = Depends(get_comment_or_404),
    user: User = Depends(get_current_user),
) -> Comment:
    if comment.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can edit only your own comments"
        )
    return comment

# Сборщик матрицы
async def get_recommendation_data(session: AsyncSession):
    # 1. Получаем все ID пользователей и видео для индексации
    users_result = await session.execute(select(User.id).order_by(User.id))
    user_ids = users_result.scalars().all()
    
    videos_result = await session.execute(select(Video.id).order_by(Video.id))
    video_ids = videos_result.scalars().all()

    # Создаем маппинги: ID -> индекс в матрице
    user_to_idx = {user_id: i for i, user_id in enumerate(user_ids)}
    video_to_idx = {vid_id: i for i, vid_id in enumerate(video_ids)}
    
    # Обратный маппинг для получения UUID видео из индекса
    idx_to_video = {i: vid_id for vid_id, i in video_to_idx.items()}

    # 2. Создаем пустую матрицу
    matrix = np.zeros((len(user_ids), len(video_ids)), dtype=np.int8)

    # 3. Заполняем матрицу лайками из БД
    likes_result = await session.execute(select(VideoLike.user_id, VideoLike.video_id))
    for u_id, v_id in likes_result.all():
        if u_id in user_to_idx and v_id in video_to_idx:
            matrix[user_to_idx[u_id]][video_to_idx[v_id]] = 1
            
    return matrix, user_to_idx, idx_to_video