import os
from typing import Generator
from src.redis_client import redis_client
from src.models.VideoModel import Video


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



# Счётчик просмотров
async def increment_view(video_id: int, ip: str):
    viewed_key = f"viewed:{video_id}:{ip}"
    views_key = f"video:views:{video_id}"

    if not await redis_client.exists(viewed_key):
        await redis_client.setex(viewed_key, 30, 1)
        await redis_client.incr(views_key)

# Получение итогового числа просмотров
async def get_total_views(video: Video) -> int:
    redis_views = await redis_client.get(f"video:views:{video.id}")
    return video.views + int(redis_views or 0)
