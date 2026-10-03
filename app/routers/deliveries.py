"""Delivery inspection and manual-retry endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Delivery, DeliveryStatus
from app.schemas import DeliveryDetailOut, DeliveryOut

router = APIRouter(prefix="/deliveries", tags=["deliveries"])


@router.get("/", response_model=list[DeliveryOut])
def list_deliveries(
    status: str | None = Query(None, description="Filter: pending | delivered | failed"),
    db: Session = Depends(get_db),
):
    q = db.query(Delivery)
    if status:
        q = q.filter(Delivery.status == status)
    return q.order_by(Delivery.created_at.desc()).all()


@router.get("/{delivery_id}", response_model=DeliveryDetailOut)
def get_delivery(delivery_id: int, db: Session = Depends(get_db)):
    d = db.get(Delivery, delivery_id)
    if not d:
        raise HTTPException(404, "Delivery not found")
    return d


@router.post("/{delivery_id}/retry", response_model=DeliveryOut)
def retry_delivery(delivery_id: int, db: Session = Depends(get_db)):
    """Reset a failed delivery so the worker picks it up again."""
    d = db.get(Delivery, delivery_id)
    if not d:
        raise HTTPException(404, "Delivery not found")
    if d.status == DeliveryStatus.delivered.value:
        raise HTTPException(400, "Delivery already succeeded")
    # Reset for another round of attempts
    d.status = DeliveryStatus.pending.value
    d.attempts = 0
    d.next_retry_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(d)
    return d
