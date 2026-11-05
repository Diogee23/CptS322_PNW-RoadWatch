"""
Fetches ID / OR / WA alerts, normalizes them, and stores them in the database.

Rules:
  * Each state is fetched and saved independently, so one failing state
    never affects the others.
  * Each record is processed independently, so one bad record is skipped
    (and logged) instead of killing the whole state.
  * If a fetch returns zero usable records we do NOT deactivate the old rows,
    because the get_* functions return [] on errors and we can't tell an
    outage from "no alerts". The API's staleness cutoff (see main.py)
    hides rows that stop being refreshed.
"""
import logging
import threading
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

import ID
import OR
import WA
from db import Alert, SessionLocal, utcnow

log = logging.getLogger("refresh")

# name -> (fetch raw records, convert one raw record to the shared schema)
SOURCES = {
    "WA DOT": (WA.get_highway_alerts, WA.process_wa_alert),
    "OR DOT": (OR.get_oregon_reports, OR.process_oregon_alert),
    "ID DOT": (ID.get_idaho_weather, ID.process_idaho_alert),
}

# Shared severity vocabulary: Low / Medium / High / Unknown.
# WSDOT's "Priority" uses Highest/High/Medium/Low/Lowest.
SEVERITY_MAP = {
    "highest": "High",
    "high": "High",
    "medium": "Medium",
    "moderate": "Medium",
    "low": "Low",
    "lowest": "Low",
}

# Status of the most recent run per source, exposed via /health.
LAST_RUN: dict[str, dict] = {}
_refresh_lock = threading.Lock()


def normalize_severity(value) -> str:
    return SEVERITY_MAP.get(str(value or "").strip().lower(), "Unknown")


def parse_time(value):
    """'2026-11-04 09:00:00 -0800' -> naive UTC datetime (or None)."""
    if not value:
        return None
    value = value.strip()
    try:
        return (
            datetime.strptime(value, "%Y-%m-%d %H:%M:%S %z")
            .astimezone(timezone.utc)
            .replace(tzinfo=None)
        )
    except ValueError:
        pass
    try:  # no offset present: assume UTC
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def collect(name, fetch, process):
    """Fetch + normalize one source. Returns (alerts, skipped_count, error)."""
    try:
        raw = fetch()
    except Exception as exc:  # the get_* functions don't catch everything
        log.exception("%s: fetch failed", name)
        return [], 0, str(exc)

    alerts, skipped = [], 0
    for item in raw or []:
        try:
            alert = process(item)
            ext_id = alert.get("ExternalId")
            if not ext_id or ext_id == "None":
                raise ValueError("record has no ID")
            alert["Severity"] = normalize_severity(alert.get("Severity"))
            alerts.append(alert)
        except Exception as exc:
            skipped += 1
            if skipped <= 3:  # don't flood the log
                log.warning("%s: skipped a record: %r", name, exc)
    return alerts, skipped, None


def save_source(session, source, alerts) -> dict:
    """Upsert alerts for one source; deactivate ones that disappeared."""
    now = utcnow()
    by_id = {a["ExternalId"]: a for a in alerts}  # also dedupes repeated IDs

    existing = {
        row.external_id: row
        for row in session.scalars(select(Alert).where(Alert.source == source))
    }

    inserted = updated = 0
    for ext_id, a in by_id.items():
        row = existing.get(ext_id)
        if row is None:
            row = Alert(source=source, external_id=ext_id)
            session.add(row)
            inserted += 1
        else:
            updated += 1
        coords = a.get("Coordinates") or {}
        row.event_category = a.get("EventCategory")
        row.headline = a.get("HeadlineDescription")
        row.severity = a["Severity"]
        row.latitude = coords.get("Latitude")
        row.longitude = coords.get("Longitude")
        row.last_updated = parse_time(a.get("LastUpdatedTime"))
        row.fetched_at = now
        row.is_active = True

    deactivated = 0
    for ext_id, row in existing.items():
        if ext_id not in by_id and row.is_active:
            row.is_active = False
            deactivated += 1

    # Housekeeping: drop rows that have been inactive for over a day.
    session.execute(
        delete(Alert).where(
            Alert.source == source,
            Alert.is_active.is_(False),
            Alert.fetched_at < now - timedelta(days=1),
        )
    )
    session.commit()
    return {"inserted": inserted, "updated": updated, "deactivated": deactivated}


def refresh_all() -> dict:
    """Refresh every source. Safe to call from the scheduler or by hand."""
    if not _refresh_lock.acquire(blocking=False):
        log.info("Refresh already running; skipping")
        return {"status": "already running"}
    try:
        for name, (fetch, process) in SOURCES.items():
            alerts, skipped, error = collect(name, fetch, process)
            info = {"time": utcnow().isoformat() + "Z", "usable": len(alerts), "skipped": skipped}

            if error:
                info["status"] = f"fetch error: {error}"
            elif not alerts:
                info["status"] = "no usable records; kept previous data"
            else:
                try:
                    with SessionLocal() as session:
                        info.update(save_source(session, name, alerts))
                    info["status"] = "ok"
                except Exception as exc:
                    log.exception("%s: database write failed", name)
                    info["status"] = f"db error: {exc}"

            LAST_RUN[name] = info
            log.info("%s: %s", name, info)
        return dict(LAST_RUN)
    finally:
        _refresh_lock.release()


if __name__ == "__main__":
    from db import init_db

    logging.basicConfig(level=logging.INFO)
    init_db()
    print(refresh_all())
