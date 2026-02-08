from pathlib import Path
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).parent.parent

class AuthData(BaseModel):
    private_key: Path = BASE_DIR /"src"/"auth"/"tokens"/"private_key.pem"
    public_key: Path = BASE_DIR /"src"/"auth"/"tokens"/"public_key.pem"
    algorithm: str = 'RS256'
    munites: int = 15
    days: int = 7


class EnvData(BaseSettings):
    DB_URL: str
    DB_URL_ASYNC: str
    SMTP_HOST: str
    SMTP_PORT: int 
    SMTP_USER: str
    SMTP_PASSWORD: str
    REDIS_HOST: str
    REDIS_PORT: int
    DROPBOX_REFRESH_TOKEN: str
    DROPBOX_APP_KEY: str
    DROPBOX_APP_SECRET: str

    model_config = SettingsConfigDict(env_file=".env.local")
    # model_config = SettingsConfigDict(env_file=".env.prod")

class Config(BaseModel):
    env_data:EnvData = EnvData()
    auth_data:AuthData = AuthData()
   

    
config = Config()