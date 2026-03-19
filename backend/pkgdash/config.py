from dataclasses import dataclass
from functools import lru_cache
import os

from dynaconf import Dynaconf

DEFAULT_API_HOST = "0.0.0.0"
DEFAULT_API_PORT = 19428
DEFAULT_FRONTEND_URL = "http://localhost:19429"

settings = Dynaconf(
    envvar_prefix="PKGDASH",
    settings_files=[
        "settings.toml",
        ".secrets.toml",
    ],
    environments=True,
    env_switcher="PKGDASH_ENV",
)


def _as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


@dataclass(frozen=True)
class RuntimeConfig:
    api_host: str
    api_port: int
    frontend_origins: list[str]


@lru_cache(maxsize=1)
def get_runtime_config() -> RuntimeConfig:
    api_host = os.getenv("PKGDASH_API_HOST", settings.get("api_host", DEFAULT_API_HOST))
    api_port = int(os.getenv("PKGDASH_API_PORT", settings.get("api_port", DEFAULT_API_PORT)))
    frontend_origins = _as_list(
        os.getenv("PKGDASH_FRONTEND_URLS")
        or settings.get("frontend_urls")
        or os.getenv("PKGDASH_FRONTEND_URL")
        or settings.get("frontend_url")
        or DEFAULT_FRONTEND_URL
    )

    return RuntimeConfig(
        api_host=api_host,
        api_port=api_port,
        frontend_origins=frontend_origins or [DEFAULT_FRONTEND_URL],
    )


if __name__ == "__main__":
    print(dict(settings))
    print(get_runtime_config())
