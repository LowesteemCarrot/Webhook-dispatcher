"""Tests for idempotent event ingestion."""


def _create_subscription(client):
    """Helper to create a subscription that listens to 'order.created'."""
    return client.post("/subscriptions/", json={
        "target_url": "http://localhost:9999/hook",
        "secret": "s3cret",
        "event_types": ["order.created"],
    })


def test_duplicate_idempotency_key_returns_same_event(client):
    _create_subscription(client)
    event_body = {"event_type": "order.created", "payload": {"id": 42}}
    headers = {"Idempotency-Key": "unique-abc-123"}

    r1 = client.post("/events/", json=event_body, headers=headers)
    r2 = client.post("/events/", json=event_body, headers=headers)

    assert r1.status_code == 202
    assert r2.status_code == 202
    assert r1.json()["id"] == r2.json()["id"]  # same event


def test_no_idempotency_key_creates_separate_events(client):
    _create_subscription(client)
    body = {"event_type": "order.created", "payload": {"id": 1}}

    r1 = client.post("/events/", json=body)
    r2 = client.post("/events/", json=body)

    assert r1.json()["id"] != r2.json()["id"]


def test_different_keys_create_different_events(client):
    _create_subscription(client)
    body = {"event_type": "order.created", "payload": {"id": 1}}

    r1 = client.post("/events/", json=body, headers={"Idempotency-Key": "key-a"})
    r2 = client.post("/events/", json=body, headers={"Idempotency-Key": "key-b"})

    assert r1.json()["id"] != r2.json()["id"]
