import logging
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, field_serializer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import refresh
from db import Alert, SessionLocal, init_db, utcnow

load_dotenv()
logging.basicConfig(level=logging.INFO)

REFRESH_MINUTES = int(os.getenv("REFRESH_MINUTES", "15"))
# Alerts not refreshed within this window are hidden (covers DOT outages).
STALE_MINUTES = int(os.getenv("STALE_MINUTES", str(REFRESH_MINUTES * 4)))
# Optional shared secret. If set, callers must send it as the X-API-Key header.
API_TOKEN = os.getenv("API_TOKEN")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        refresh.refresh_all,
        "interval",
        minutes=REFRESH_MINUTES,
        next_run_time=datetime.now(timezone.utc),  # also run once at startup
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Road Alerts API", lifespan=lifespan)


def require_key(x_api_key: str | None = Header(default=None)):
    if API_TOKEN and not (x_api_key and secrets.compare_digest(x_api_key, API_TOKEN)):
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key")


def get_db():
    with SessionLocal() as session:
        yield session


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    external_id: str
    event_category: str | None
    headline: str | None
    severity: str
    latitude: float | None
    longitude: float | None
    last_updated: datetime | None  # UTC
    fetched_at: datetime           # UTC

    @field_serializer("last_updated", "fetched_at")
    def _utc(self, dt: datetime | None):
        return dt.isoformat() + "Z" if dt else None


@app.get("/alerts", response_model=list[AlertOut], dependencies=[Depends(require_key)])
def list_alerts(db: Session = Depends(get_db)):
    """All currently active alerts from WA, OR and ID."""
    cutoff = utcnow() - timedelta(minutes=STALE_MINUTES)
    stmt = (
        select(Alert)
        .where(Alert.is_active.is_(True), Alert.fetched_at >= cutoff)
        .order_by(Alert.source, Alert.id)
    )
    return db.scalars(stmt).all()


@app.get("/health")
def health(db: Session = Depends(get_db)):
    counts = dict(
        db.execute(
            select(Alert.source, func.count()).where(Alert.is_active.is_(True)).group_by(Alert.source)
        ).all()
    )
    return {"active_alerts_by_source": counts, "last_refresh": refresh.LAST_RUN}


@app.post("/refresh", dependencies=[Depends(require_key)])
def manual_refresh():
    """Force a refresh now (handy for testing)."""
    return refresh.refresh_all()
