import argparse

import uvicorn
from pkgdash import logger
from pkgdash.config import get_runtime_config

from .app import app


def main():
    runtime_config = get_runtime_config()
    parser = argparse.ArgumentParser("Package Dashboard Server")
    parser.add_argument("-p", "--port", default=runtime_config.api_port, type=int, help="Port to run on")
    parser.add_argument("-o", "--host", default=runtime_config.api_host, help="Host to run on")
    parser.add_argument(
        "-r",
        "--reload",
        action="store_true",
        default=False,
        help="Reload on code changes",
    )
    args = parser.parse_args()
    logger.info("Starting Package Dashboard API on {}:{}", args.host, args.port)

    uvicorn.run(
        "pkgdash.serve.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
