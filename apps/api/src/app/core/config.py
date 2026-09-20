from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_name: str = "IITGN Alumni & Donor CRM API"
    environment: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/iitgn_crm"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Identity provider seam (see ADR-003).
    # "password" = dev/staging-only local credential check, never production.
    # "google"   = production Sign in with Google (requires google_client_id).
    identity_provider: str = "password"
    google_client_id: str = ""

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:5175"]

    # Demo bootstrap (staging/demo only — never production; see
    # app.db.demo_bootstrap). When demo_seed is true, every boot ensures
    # demo accounts and fictional demo data so a fresh database behaves
    # like a locally seeded one.
    demo_seed: bool = False
    demo_password: str = ""
    demo_alumni_count: int = 100

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, v: str) -> str:
        # Managed providers (e.g. Render) hand out postgres:// or plain
        # postgresql:// URLs, but this service's async engine needs the
        # postgresql+asyncpg:// driver scheme. Normalise here so the same
        # image runs locally and on Render without manual URL surgery.
        if isinstance(v, str):
            if v.startswith("postgres://"):
                v = "postgresql://" + v[len("postgres://"):]
            if v.startswith("postgresql://"):
                v = "postgresql+asyncpg://" + v[len("postgresql://"):]
        return v


settings = Settings()
