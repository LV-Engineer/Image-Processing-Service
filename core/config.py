from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    app_env: str = 'development'
    database_url: str

    redis_url: str

    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int

    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region: str = 'us-east-1'
    aws_s3_bucket: str

settings = Settings()