import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, JSON, String,
)
from sqlalchemy.orm import relationship

from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class DeliveryStatus(str, enum.Enum):
    pending = "pending"
    delivered = "delivered"
    failed = "failed"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    target_url = Column(String, nullable=False)
    secret = Column(String, nullable=False)          # used for HMAC signing
    event_types = Column(JSON, nullable=False)        # e.g. ["order.created", "user.signup"]
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    deliveries = relationship("Delivery", back_populates="subscription")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    idempotency_key = Column(String, unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=_utcnow)

    deliveries = relationship("Delivery", back_populates="event")


class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    status = Column(String, default=DeliveryStatus.pending.value)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=5)
    next_retry_at = Column(DateTime, default=_utcnow)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    event = relationship("Event", back_populates="deliveries")
    subscription = relationship("Subscription", back_populates="deliveries")
    attempt_logs = relationship(
        "DeliveryAttempt", back_populates="delivery",
        order_by="DeliveryAttempt.attempt_number",
    )


class DeliveryAttempt(Base):
    __tablename__ = "delivery_attempts"

    id = Column(Integer, primary_key=True, index=True)
    delivery_id = Column(Integer, ForeignKey("deliveries.id"), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    status_code = Column(Integer, nullable=True)      # HTTP status or None on network error
    error = Column(String, nullable=True)              # error message if any
    created_at = Column(DateTime, default=_utcnow)

    delivery = relationship("Delivery", back_populates="attempt_logs")
