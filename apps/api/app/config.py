from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # groq | openrouter | ollama | anthropic
    llm_provider: str = "groq"
    specwright_model_extract: str = "openai/gpt-oss-120b"
    specwright_model_plan: str = "openai/gpt-oss-120b"
    specwright_model_review: str = "openai/gpt-oss-120b"

    groq_api_key: str = ""
    openrouter_api_key: str = ""
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434/v1"

    appwrite_endpoint: str = "https://cloud.appwrite.io/v1"
    appwrite_project_id: str = ""
    appwrite_api_key: str = ""

    redis_url: str = "redis://localhost:6379"
    linear_api_key: str = ""
    web_origin: str = "http://localhost:3000"


settings = Settings()