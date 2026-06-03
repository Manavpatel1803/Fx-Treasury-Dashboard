import asyncio
from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app.fx_service import collect_snapshot_for_pair, get_default_pairs
from app.config import settings


scheduler = BackgroundScheduler()


def scheduled_snapshot_job():
    async def run():
        db = SessionLocal()

        try:
            for pair in get_default_pairs():
                await collect_snapshot_for_pair(db, pair)
        finally:
            db.close()

    asyncio.run(run())


def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            scheduled_snapshot_job,
            "interval",
            minutes=settings.SNAPSHOT_INTERVAL_MINUTES,
            id="fx_snapshot_job",
            replace_existing=True,
        )

        scheduler.start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()