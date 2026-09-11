from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


_ROOT = Path(__file__).resolve().parents[2]  # backend/
_PROJECT = _ROOT.parent  # gb10-llm-bench-platform/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LLMBENCH_", env_file=".env", extra="ignore")

    app_name: str = "GB10 LLM Bench"
    db_path: Path = _ROOT / "llmbench.db"
    run_root: Path = _PROJECT / "runs"
    recipe_root: Path = _PROJECT / "recipes"
    llama_bench: str = "llama-bench"
    llama_server: str = "llama-server"
    llama_server_url: str = ""
    cors_origins: str = ""


settings = Settings()
