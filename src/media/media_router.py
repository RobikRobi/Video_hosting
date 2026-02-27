import pathlib
import uuid
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, func, select
from sqlalchemy.orm import selectinload
from src.db import get_session
from src.config import config
from src.media.media_utillits import get_video_or_404, get_video_owned_by_user
from src.media.media_utillits import get_user_video_like, get_user_channel, get_comment_or_404
from src.media.media_utillits import check_comment_owner
from src.get_current_user import get_current_user
from src.models.UserModel import User
from src.models.VideoModel import Video, VideoLike
from src.models.CommentModel import Comment
from src.models.ChannelModel import Channel
from src.media.media_shema import VideoShow, CommentCreate, CommentOut, CommentUpdate
from src.media.media_utillits import get_recommendation_data
from src.media.recommendation_service import VideoRecommender




app = APIRouter(prefix="/media", tags=["Media"])

# app = APIRouter(prefix="/videos", tags=["Videos"])
dbx = dropbox.Dropbox(
    oauth2_refresh_token=config.env_data.DROPBOX_REFRESH_TOKEN,
    app_key=config.env_data.DROPBOX_APP_KEY,
    app_secret=config.env_data.DROPBOX_APP_SECRET,
)

CHUNK_SIZE = 4 * 1024 * 1024

# Функция для загрузки видео на dropbox
async def upload_to_dropbox(file: UploadFile, dropbox_path: str) -> str:
    first_chunk = await file.read(CHUNK_SIZE)

    session = dbx.files_upload_session_start(first_chunk)
    cursor = dropbox.files.UploadSessionCursor(
        session_id=session.session_id,
        offset=len(first_chunk),
    )

    while chunk := await file.read(CHUNK_SIZE):
        dbx.files_upload_session_append_v2(chunk, cursor)
        cursor.offset += len(chunk)

    commit = dropbox.files.CommitInfo(path=dropbox_path, mode=WriteMode.overwrite)
    dbx.files_upload_session_finish(b"", cursor, commit)

    shared = dbx.sharing_create_shared_link_with_settings(dropbox_path)
    return shared.url.replace("?dl=0", "?raw=1")

# Загрузка видео в dropbox
@app.post("/save", status_code=201)
async def upload_video(
    title: str = Form(...),
    description: str = Form(...),
    channel_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    ext = pathlib.Path(file.filename).suffix.lower()
    if ext != ".mp4":
        raise HTTPException(400, "Only .mp4 allowed")

    video_id = uuid.uuid4()
    dropbox_path = f"/videos/{video_id}{ext}"

    try:
        dropbox_url = await upload_to_dropbox(file, dropbox_path)

        video = Video(
            id=video_id,
            title=title,
            description=description,
            channel_id=channel_id,
            url=dropbox_url,
            storage_path=dropbox_path,
            author_id=user.id,
        )

        session.add(video)
        await session.commit()
        await session.refresh(video)

        return video

    except Exception as e:
        await session.rollback()
        raise HTTPException(500, f"Upload failed: {e}")

    finally:
        await file.close()


# Рекомендации видео
@app.get("/recommendations")
async def get_video_recommendations(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    # Получаем данные и маппинги
    matrix, user_to_idx, idx_to_video = await get_recommendation_data(session)
    
    if user.id not in user_to_idx:
        return {"items": []} # Новый пользователь без лайков

    recommender = VideoRecommender()
    video_uuids = recommender.get_recommendations(
        matrix, 
        user_to_idx[user.id], 
        idx_to_video, 
        n=10
    )

    # Загружаем объекты видео из БД по списку UUID
    result = await session.execute(
        select(Video).where(Video.id.in_(video_uuids))
    )
    return result.scalars().all()


# Фильтрация видео
@app.get("/filter")
async def filters(title:str=None, 
                  description:str=None, 
                  session: AsyncSession = Depends(get_session)):
     if not title and not description:
         videos = await session.scalars(select(Video))
     elif not title:
         videos = await session.scalars(select(Video).
                                 filter(Video.description.ilike(f"%{description}%")))
     elif not description:
         videos = await session.scalars(select(Video).
                                 filter(Video.title.ilike(f"%{title}%")))
     else:
         videos = await session.scalars(select(Video).
                                 filter(Video.description.ilike(f"%{title}%")), 
                                 (Video.description.ilike(f"%{description}%")))
     
     return videos.all()



# Стриминг видео
@app.get("/video/{video_id}")
async def get_video_stream(
    video: Video = Depends(get_video_or_404),
    session: AsyncSession = Depends(get_session),
):
    # увеличиваем просмотры
    await session.execute(
        update(Video)
        .where(Video.id == video.id)
        .values(views=func.coalesce(Video.views, 0) + 1)
    )
    await session.commit()

    # редирект на Dropbox CDN
    return RedirectResponse(
        url=video.url,
        status_code=302
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

    try:
        # 1. удаляем файл из Dropbox
        try:
            dbx.files_delete_v2(video.storage_path)
        except ApiError as e:
            # если файл уже удалён — не критично
            if e.error.is_path_lookup():
                pass
            else:
                raise
        # 2. удаляем запись из БД
        await session.delete(video)
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete video: {e}",
        )
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