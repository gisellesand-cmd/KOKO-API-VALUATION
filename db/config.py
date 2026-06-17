from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://koko:koko@localhost:5432/koko_mls"
    echo_sql: bool = False


settings = Settings()
