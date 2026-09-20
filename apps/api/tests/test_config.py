from app.core.config import Settings


def test_render_postgres_scheme_gets_asyncpg_driver():
    settings = Settings(database_url="postgres://user:pass@host:5432/iitgn_crm")
    assert settings.database_url == "postgresql+asyncpg://user:pass@host:5432/iitgn_crm"


def test_plain_postgresql_scheme_gets_asyncpg_driver():
    settings = Settings(database_url="postgresql://user:pass@host:5432/iitgn_crm")
    assert settings.database_url == "postgresql+asyncpg://user:pass@host:5432/iitgn_crm"


def test_asyncpg_url_left_untouched():
    url = "postgresql+asyncpg://postgres:postgres@localhost:5432/iitgn_crm"
    assert Settings(database_url=url).database_url == url
