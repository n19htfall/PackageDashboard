from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination

from pkgdash.config import get_runtime_config
from pkgdash.models.connector.mongo import create_engine

from .routes import pkg, repo


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_engine()
    yield


def create_app() -> FastAPI:
    runtime_config = get_runtime_config()
    app = FastAPI(title="Package Dashboard", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=runtime_config.frontend_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(pkg.api, prefix="/api/pkg", tags=["Package"])
    app.include_router(repo.api, prefix="/api/repo", tags=["Repository"])
    add_pagination(app)

    @app.get("/api/health", tags=["Health"])
    async def healthcheck():
        return {"status": "ok"}

    return app


app = create_app()
