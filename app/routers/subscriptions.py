"""CRUD endpoints for webhook subscriptions."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Subscription
from app.schemas import SubscriptionCreate, SubscriptionOut, SubscriptionUpdate

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post("/", response_model=SubscriptionOut, status_code=201)
def create_subscription(body: SubscriptionCreate, db: Session = Depends(get_db)):
    sub = Subscription(
        target_url=str(body.target_url),
        secret=body.secret,
        event_types=body.event_types,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@router.get("/", response_model=list[SubscriptionOut])
def list_subscriptions(db: Session = Depends(get_db)):
    return db.query(Subscription).all()


@router.get("/{sub_id}", response_model=SubscriptionOut)
def get_subscription(sub_id: int, db: Session = Depends(get_db)):
    sub = db.get(Subscription, sub_id)
    if not sub:
        raise HTTPException(404, "Subscription not found")
    return sub


@router.patch("/{sub_id}", response_model=SubscriptionOut)
def update_subscription(sub_id: int, body: SubscriptionUpdate, db: Session = Depends(get_db)):
    sub = db.get(Subscription, sub_id)
    if not sub:
        raise HTTPException(404, "Subscription not found")
    # Only update fields that were explicitly set
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "target_url" and value is not None:
            value = str(value)
        setattr(sub, field, value)
    db.commit()
    db.refresh(sub)
    return sub


@router.delete("/{sub_id}", status_code=204)
def delete_subscription(sub_id: int, db: Session = Depends(get_db)):
    sub = db.get(Subscription, sub_id)
    if not sub:
        raise HTTPException(404, "Subscription not found")
    db.delete(sub)
    db.commit()
