from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, HttpUrl


# ── Subscriptions ──────────────────────────────────────────

class SubscriptionCreate(BaseModel):
    target_url: HttpUrl
    secret: str
    event_types: list[str]


class SubscriptionUpdate(BaseModel):
    target_url: HttpUrl | None = None
    secret: str | None = None
    event_types: list[str] | None = None
    active: bool | None = None


class SubscriptionOut(BaseModel):
    id: int
    target_url: str
    event_types: list[str]
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Events ─────────────────────────────────────────────────

class EventCreate(BaseModel):
    event_type: str
    payload: dict[str, Any]


class EventOut(BaseModel):
    id: int
    event_type: str
    payload: dict[str, Any]
    idempotency_key: str | None
    created_at: datetime
    deliveries_created: int  # how many delivery records were made

    model_config = {"from_attributes": True}


# ── Deliveries ─────────────────────────────────────────────

class AttemptOut(BaseModel):
    attempt_number: int
    status_code: int | None
    error: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DeliveryOut(BaseModel):
    id: int
    event_id: int
    subscription_id: int
    status: str
    attempts: int
    max_attempts: int
    next_retry_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeliveryDetailOut(DeliveryOut):
    attempt_logs: list[AttemptOut] = []
