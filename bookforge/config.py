"""Central, env-driven configuration for BookForge.

Gemini credentials are read directly by google-genai from the environment
(GOOGLE_API_KEY, or GOOGLE_GENAI_USE_VERTEXAI + GOOGLE_CLOUD_PROJECT/LOCATION)
and are intentionally NOT part of Settings.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Every field maps to BOOKFORGE_<NAME> env vars."""

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="BOOKFORGE_", extra="ignore"
    )

    # --- LLM routing -------------------------------------------------------
    analyst_model: str = "nvidia/nemotron-3-ultra-550b-a55b"
    writer_model: str = "nvidia/nemotron-3-ultra-550b-a55b"
    critic_model: str = "nvidia/nemotron-3-ultra-550b-a55b"
    openai_api_base: str = "https://integrate.api.nvidia.com/v1"
    openai_api_key: str = ""  # set via BOOKFORGE_OPENAI_API_KEY (never hardcode)

    # --- Media pipeline ----------------------------------------------------
    frame_interval_sec: int = 5  # screenshot cadence (per the flow)
    frame_phash_threshold: int = 6  # hamming distance <= -> duplicate
    max_frames_per_chapter: int = 12  # curated figures per chapter
    download_resolution: int = 480  # capped video height
    whisper_model: str = "base"  # faster-whisper size (fallback STT)

    # --- Scope / safety rails ----------------------------------------------
    max_videos: int | None = None  # None = entire channel
    min_video_duration_sec: int = 30  # skip shorts/trailers
    max_video_duration_sec: int = 3 * 3600

    # --- Quality loop ------------------------------------------------------
    qa_max_iterations: int = 3
    compile_latex: bool = True  # disable on hosts without pdflatex

    # --- Parallelization (opt-in for safety) ------------------------------
    max_concurrent_videos: int = 1  # 1=sequential (safe default), 2-3=parallel
    enable_parallel_videos: bool = False  # explicit opt-in required

    # --- Housekeeping ------------------------------------------------------
    workspace_root: Path = Path("data")
    log_level: str = "INFO"

    @property
    def workspace_root_abs(self) -> Path:
        return self.workspace_root.expanduser().resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()


def configure_logging(level: str = "INFO", json_format: bool = False) -> None:
    """Configure structured logging for BookForge."""
    import logging

    if json_format:
        fmt = '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}'
    else:
        fmt = "%(asctime)s %(levelname)-7s [%(name)s] %(message)s"

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    # Quiet noisy third-party loggers
    for noisy in ("urllib3", "httpcore", "httpx", "google.auth", "yt_dlp"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
