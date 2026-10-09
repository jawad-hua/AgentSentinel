from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./data/agentsentinel.db"
    allowed_hosts: str = "127.0.0.1,localhost,[::1]"

    @property
    def hosts(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]

    @field_validator("allowed_hosts")
    @classmethod
    def explicit_hosts(cls, value: str) -> str:
        if not value.strip() or "*" in value or "/" in value:
            raise ValueError("Configure explicit hosts without wildcards or URLs")
        return value
    admin_api_token: SecretStr
    ingest_api_token: SecretStr
    n8n_base_url: str = "http://127.0.0.1:5678"
    n8n_api_key: SecretStr = SecretStr("")
    groq_api_key: SecretStr = SecretStr("")
    groq_model: str = "llama-3.3-70b-versatile"
    http_timeout_seconds: float = 15
    kill_switch: bool = True
    chaos_enabled: bool = False
    chaos_workflow_ids: str = ""

    @property
    def chaos_targets(self) -> set[str]:
        return {x.strip() for x in self.chaos_workflow_ids.split(",") if x.strip()}

    repairs_enabled: bool = False
    repair_workflow_ids: str = ""
    n8n_write_api_key: SecretStr = SecretStr("")
    snapshot_encryption_key: SecretStr = SecretStr("")

    @field_validator("snapshot_encryption_key")
    @classmethod
    def valid_snapshot_key(cls, value: SecretStr) -> SecretStr:
        if value.get_secret_value():
            try:
                Fernet(value.get_secret_value().encode())
            except (ValueError, TypeError):
                raise ValueError("Snapshot key must be a valid Fernet key") from None
        return value

    @property
    def repair_targets(self) -> set[str]:
        return {item.strip() for item in self.repair_workflow_ids.split(",") if item.strip()}

    analysis_enabled: bool = True
    analysis_auto_new: bool = True
    analysis_daily_limit: int = 20
    groq_timeout_seconds: int = 60
    monitoring_enabled: bool = True

    @field_validator("analysis_daily_limit")
    @classmethod
    def bounded_analysis_budget(cls, value: int) -> int:
        if not 1 <= value <= 100:
            raise ValueError("Analysis budget must be between 1 and 100 runs per 24 hours")
        return value

    @field_validator("groq_timeout_seconds")
    @classmethod
    def bounded_groq_timeout(cls, value: int) -> int:
        if not 10 <= value <= 60:
            raise ValueError("Groq timeout must be between 10 and 60 seconds")
        return value

    poll_interval_seconds: int = 30
    monitoring_lookback_hours: int = 24

    @field_validator("poll_interval_seconds")
    @classmethod
    def bounded_poll(cls, value: int) -> int:
        if not 10 <= value <= 300:
            raise ValueError("Poll interval must be between 10 and 300 seconds")
        return value

    @field_validator("monitoring_lookback_hours")
    @classmethod
    def bounded_lookback(cls, value: int) -> int:
        if not 1 <= value <= 168:
            raise ValueError("Lookback must be between 1 and 168 hours")
        return value

    @field_validator("admin_api_token", "ingest_api_token")
    @classmethod
    def strong_token(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("API tokens must contain at least 32 characters")
        return value

    @field_validator("http_timeout_seconds")
    @classmethod
    def bounded_timeout(cls, value: float) -> float:
        if not 1 <= value <= 60:
            raise ValueError("Timeout must be between 1 and 60 seconds")
        return value

    @field_validator("n8n_base_url")
    @classmethod
    def valid_origin(cls, value: str) -> str:
        url = urlsplit(value)
        if url.scheme not in {"http", "https"} or not url.hostname:
            raise ValueError("n8n requires an HTTP(S) URL")
        if url.username or url.password or url.query or url.fragment:
            raise ValueError("Do not embed credentials, query or fragment in n8n URL")
        return value.rstrip("/")

    @model_validator(mode="after")
    def separate_tokens(self) -> "Settings":
        if self.admin_api_token == self.ingest_api_token:
            raise ValueError("Admin and ingest tokens must differ")
        return self
