import os
from typing import Generator
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

