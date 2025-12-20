import redis.asyncio as redis
from src.config import config

redis_client = redis.Redis(
    host=config.env_data.REDIS_HOST,  # берём из .env
    port=config.env_data.REDIS_PORT,  # берём из .env
    db=0,
    decode_responses=True  # Чтобы строки приходили как строки, а не байты
)