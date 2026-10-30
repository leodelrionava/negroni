"""Configuracion global cargada desde variables de entorno (.env)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str = ""
    agent_model: str = "claude-haiku-4-5-20251001"

    whatsapp_access_token: str = ""
    whatsapp_verify_token: str = "negroni-verifica-2026"
    graph_api_version: str = "v21.0"

    tenants_dir: str = "tenants"
    history_turns: int = 12
    db_path: str = "negroni.db"


settings = Settings()
