from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    base_url: str
    allowed_users: list[str]
    openid_configuration: str
    database_url: str
    client_id: str
    client_secret: str
    weaviate_url: str
    update_interval: int = 24 * 60 * 60


settings = Settings()
