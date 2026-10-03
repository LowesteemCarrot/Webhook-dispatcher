"""End-to-end test: event -> delivery -> worker retries -> success."""

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.models import Delivery, DeliveryAttempt, DeliveryStatus
from app.worker import _deliver_one


def _setup(client):
    """Create a subscription + event, return the delivery id."""
    client.post("/subscriptions/", json={
        "target_url": "http://localhost:9999/hook",
        "secret": "test-secret",
        "event_types": ["order.created"],
    })
    resp = client.post("/events/", json={
        "event_type": "order.created",
        "payload": {"amount": 99},
    })
    assert resp.status_code == 202
    # Get the delivery
    deliveries = client.get("/deliveries/").json()
    assert len(deliveries) == 1
    return deliveries[0]["id"]


def _make_response(status_code):
    """Build a minimal httpx.Response."""
    return httpx.Response(status_code=status_code, request=httpx.Request("POST", "http://x"))


@pytest.mark.asyncio
async def test_delivery_succeeds_on_200(client, db):
    delivery_id = _setup(client)

    mock_resp = _make_response(200)
    with patch("app.worker.SessionLocal", return_value=db):
        with patch("app.worker.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await _deliver_one(delivery_id)

    delivery = db.get(Delivery, delivery_id)
    assert delivery.status == DeliveryStatus.delivered.value
    assert delivery.attempts == 1


@pytest.mark.asyncio
async def test_delivery_retries_on_500_then_succeeds(client, db):
    delivery_id = _setup(client)

    call_count = 0

    async def fake_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            return _make_response(500)
        return _make_response(200)

    with patch("app.worker.SessionLocal", return_value=db):
        with patch("app.worker.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=fake_post)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            # Attempt 1: 500
            await _deliver_one(delivery_id)
            d = db.get(Delivery, delivery_id)
            assert d.status == DeliveryStatus.pending.value

            # Attempt 2: 500
            await _deliver_one(delivery_id)
            d = db.get(Delivery, delivery_id)
            assert d.status == DeliveryStatus.pending.value

            # Attempt 3: 200
            await _deliver_one(delivery_id)
            d = db.get(Delivery, delivery_id)
            assert d.status == DeliveryStatus.delivered.value
            assert d.attempts == 3

    # Verify attempt logs
    attempts = db.query(DeliveryAttempt).filter_by(delivery_id=delivery_id).all()
    assert len(attempts) == 3
    assert attempts[0].status_code == 500
    assert attempts[2].status_code == 200


@pytest.mark.asyncio
async def test_delivery_fails_on_non_retryable_4xx(client, db):
    delivery_id = _setup(client)

    mock_resp = _make_response(404)
    with patch("app.worker.SessionLocal", return_value=db):
        with patch("app.worker.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await _deliver_one(delivery_id)

    delivery = db.get(Delivery, delivery_id)
    assert delivery.status == DeliveryStatus.failed.value
