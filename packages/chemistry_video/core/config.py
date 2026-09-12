from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "chemistry-video-service"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # ADK / Gemini. ADK 2.x reads these names directly from the environment.
    google_genai_use_enterprise: bool = True
    google_cloud_project: str = Field(min_length=1)
    google_cloud_location: str = "global"
    gemini_model: str = "gemini-3.1-flash-lite"

    # Veo is regional even though Gemini is global.
    veo_model: str = "veo-3.1-lite-generate-001"
    veo_location: str = "us-central1"
    veo_duration_seconds: int = 8
    veo_aspect_ratio: str = "16:9"
    veo_resolution: str = "720p"
    veo_poll_seconds: int = 10
    veo_output_gcs_uri: str | None = None

    artifact_dir: Path = Path("artifacts")

    def ensure_runtime_dirs(self) -> None:
        self.artifact_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_runtime_dirs()
    return settings
