from aiochclient import ChClient
from aiohttp import ClientSession

from pkgdash import settings, logger

async def create_engine(s: ClientSession) -> ChClient:
    """
    Creates a new clickhouse engine
    """
    client = ChClient(s, url=settings.clickhouse.url, database=settings.clickhouse.db, 
                      user=settings.clickhouse.user, password=settings.clickhouse.password)
    alive = await client.is_alive()
    if not alive:
        logger.error(f"Clickhouse is not alive: {settings.clickhouse.url}")
        raise Exception("Clickhouse is not alive")
    return client


if __name__ == '__main__':
    import asyncio

    async def main():
        async with ClientSession() as s:
            await create_engine(s)

    asyncio.run(main())