from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    specwright_model_extract: str = "claude-haiku-5-5"
    specwright_model_plan: str = "claude-sonnet-5-5"
    specwright_model_review: str = "claude-sonnet-5-5"

    appwrite_endpoint: str = "https://cloud.appwrite.io/v1"
    appwrite_project_id: str = ""
    appwrite_api_key: str = ""

    redis_url: str = "redis://localhost:6379"
    linear_api_key: str = ""
    web_origin: str = "http://localhost:3000"


settings = Settings()
