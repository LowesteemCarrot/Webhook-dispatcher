"""Event ingestion endpoint."""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Delivery, Event, Subscription
from app.schemas import EventCreate, EventOut

router = APIRouter(prefix="/events", tags=["events"])


@router.post("/", response_model=EventOut, status_code=202)
def ingest_event(
    body: EventCreate,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    # ── Idempotency check ──────────────────────────────────
    if idempotency_key:
        existing = (
            db.query(Event)
            .filter(Event.idempotency_key == idempotency_key)
            .first()
        )
        if existing:
            count = db.query(Delivery).filter(Delivery.event_id == existing.id).count()
            return EventOut(
                id=existing.id,
                event_type=existing.event_type,
                payload=existing.payload,
                idempotency_key=existing.idempotency_key,
                created_at=existing.created_at,
                deliveries_created=count,
            )

    # ── Create the event ───────────────────────────────────
    event = Event(
        event_type=body.event_type,
        payload=body.payload,
        idempotency_key=idempotency_key,
    )
    db.add(event)
    db.flush()  # get event.id without committing yet

    # ── Fan out to matching subscriptions ──────────────────
    subs = (
        db.query(Subscription)
        .filter(Subscription.active == True)  # noqa: E712
        .all()
    )
    deliveries_created = 0
    for sub in subs:
        if body.event_type in sub.event_types:
            db.add(Delivery(event_id=event.id, subscription_id=sub.id))
            deliveries_created += 1

    db.commit()
    db.refresh(event)

    return EventOut(
        id=event.id,
        event_type=event.event_type,
        payload=event.payload,
        idempotency_key=event.idempotency_key,
        created_at=event.created_at,
        deliveries_created=deliveries_created,
    )
