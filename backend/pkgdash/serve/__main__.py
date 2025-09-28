import argparse
import logging
import os

import uvicorn
from fastapi import FastAPI

from pkgdash import settings, logger
from pkgdash.models.connector.mongo import create_engine
from .routes import pkg, repo
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from ..config import FRONTED_URL


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_engine()
    yield


app = FastAPI(title="Package Dashboard", version="0.1.0", lifespan=lifespan)

app.include_router(pkg.api, prefix="/api/pkg", tags=["Package"])
app.include_router(repo.api, prefix="/api/repo", tags=["Repository"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTED_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser("Package Dashboard Server")
    parser.add_argument("-p", "--port", default=19428, type=int, help="Port to run on")
    parser.add_argument("-o", "--host", default="0.0.0.0", help="Host to run on")
    parser.add_argument(
        "-r",
        "--reload",
        action="store_true",
        default=False,
        help="Reload on code changes",
    )
    args = parser.parse_args()
    logger.info(f"Starting uvicorn server on port {args.port}")

    uvicorn.run(
        "pkgdash.serve.__main__:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
