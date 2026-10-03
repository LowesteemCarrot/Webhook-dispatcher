"""Background worker that delivers pending webhooks."""

import asyncio
import json
import logging
import random
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Delivery, DeliveryAttempt, DeliveryStatus
from app.signing import SIGNATURE_HEADER, sign_payload

logger = logging.getLogger("webhook.worker")

# ── Backoff helpers ────────────────────────────────────────────

BASE_DELAY = 2          # seconds
MAX_DELAY = 300         # 5 minutes cap
JITTER_RANGE = 0.5      # ±50 % jitter


def backoff_delay(attempt: int) -> float:
    """Exponential backoff: base * 2^attempt, capped, plus jitter."""
    delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
    jitter = delay * random.uniform(-JITTER_RANGE, JITTER_RANGE)
    return max(0, delay + jitter)


def should_retry(status_code: int) -> bool:
    """Retry on 5xx, 429; don't retry other 4xx."""
    if status_code == 429:
        return True
    if 500 <= status_code < 600:
        return True
    return False


# ── Core delivery logic ───────────────────────────────────────

async def _deliver_one(delivery_id: int) -> None:
    """Attempt to POST the webhook for a single delivery."""
    db: Session = SessionLocal()
    try:
        delivery = db.get(Delivery, delivery_id)
        if not delivery or delivery.status != DeliveryStatus.pending.value:
            return

        event = delivery.event
        sub = delivery.subscription

        # Build the payload
        body = json.dumps({
            "event_id": event.id,
            "event_type": event.event_type,
            "payload": event.payload,
        }).encode()

        signature = sign_payload(body, sub.secret)

        # ── HTTP POST ──────────────────────────────────────
        status_code = None
        error_msg = None
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    sub.target_url,
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        SIGNATURE_HEADER: signature,
                    },
                )
            status_code = resp.status_code
        except httpx.TimeoutException:
            error_msg = "Timeout"
        except httpx.RequestError as exc:
            error_msg = str(exc)

        # ── Record the attempt ─────────────────────────────
        delivery.attempts += 1
        db.add(DeliveryAttempt(
            delivery_id=delivery.id,
            attempt_number=delivery.attempts,
            status_code=status_code,
            error=error_msg,
        ))

        # ── Decide outcome ─────────────────────────────────
        if status_code and 200 <= status_code < 300:
            delivery.status = DeliveryStatus.delivered.value
            logger.info("Delivery %d succeeded (HTTP %d)", delivery.id, status_code)

        elif delivery.attempts >= delivery.max_attempts:
            # Dead letter
            delivery.status = DeliveryStatus.failed.value
            logger.warning("Delivery %d failed after %d attempts", delivery.id, delivery.attempts)

        elif status_code and not should_retry(status_code):
            # Non-retryable client error (4xx except 429)
            delivery.status = DeliveryStatus.failed.value
            logger.warning("Delivery %d got non-retryable HTTP %d", delivery.id, status_code)

        else:
            # Schedule retry
            delay = backoff_delay(delivery.attempts)
            delivery.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
            logger.info(
                "Delivery %d attempt %d failed, retrying in %.1fs",
                delivery.id, delivery.attempts, delay,
            )

        db.commit()
    finally:
        db.close()


# ── Worker loop ───────────────────────────────────────────────

POLL_INTERVAL = 2  # seconds between polls


async def worker_loop() -> None:
    """Continuously poll for pending deliveries and process them."""
    logger.info("Worker started")
    while True:
        db: Session = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            pending = (
                db.query(Delivery.id)
                .filter(
                    Delivery.status == DeliveryStatus.pending.value,
                    Delivery.next_retry_at <= now,
                )
                .limit(20)
                .all()
            )
        finally:
            db.close()

        if pending:
            # Process batch concurrently
            await asyncio.gather(*[_deliver_one(row.id) for row in pending])
        else:
            await asyncio.sleep(POLL_INTERVAL)
