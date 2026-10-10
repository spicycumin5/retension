"""Hourly job: python -m app.jobs.send_digests"""
import asyncio
import logging

from app import clock
from app.db import SessionLocal, engine
from app.digest import send_due_digests


async def main() -> None:
    async with SessionLocal() as session:
        result = await send_due_digests(session, clock.now())
    await engine.dispose()
    logging.getLogger("recall.digest").info(
        "digests sent=%d nothing_due=%d failed=%d", result.sent, result.skipped_nothing_due, result.failed
    )
    if result.failed:
        raise SystemExit(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    asyncio.run(main())
