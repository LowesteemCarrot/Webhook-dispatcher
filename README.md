# Event & Webhook Dispatcher Engine

A lightweight webhook delivery system built with **FastAPI**, **SQLAlchemy** (SQLite), and **httpx**.
It lets you register subscriptions, ingest events, and reliably deliver them with retries and HMAC signing.

## Features

- **Subscription CRUD** – register target URLs with event types and signing secrets.
- **Event ingestion** – POST events with an optional `Idempotency-Key` header.
- **Fan-out** – each event is matched against active subscriptions; delivery records are created in the DB.
- **Background worker** – an asyncio loop picks up pending deliveries and POSTs them.
- **Retries** – exponential backoff with jitter, max 5 attempts. Retries on 5xx, 429, and timeouts.
- **HMAC-SHA256 signing** – every delivery includes an `X-Webhook-Signature` header.
- **Delivery logs** – inspect every attempt with status codes and errors. Manual retry support.

## Project Structure

```
app/
├── main.py            # FastAPI app + lifespan (worker startup)
├── models.py          # SQLAlchemy models
├── schemas.py         # Pydantic schemas
├── database.py        # Engine, session, Base
├── signing.py         # HMAC-SHA256 helpers
├── worker.py          # Background delivery worker
└── routers/
    ├── subscriptions.py
    ├── events.py
    └── deliveries.py
tests/
├── conftest.py
├── test_backoff.py
├── test_signing.py
├── test_idempotency.py
└── test_retry_e2e.py
scripts/
└── mock_receiver.py   # Randomly-failing test server
```

## Setup

```bash
# Create a virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Run the Server

```bash
uvicorn app.main:app --reload
```

The API docs are at http://127.0.0.1:8000/docs

## Run Tests

```bash
pytest -v
```

## curl Examples

### 1. Create a subscription

```bash
curl -X POST http://localhost:8000/subscriptions/ \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "http://localhost:9999/hook",
    "secret": "my-secret-key",
    "event_types": ["order.created", "user.signup"]
  }'
```

### 2. List subscriptions

```bash
curl http://localhost:8000/subscriptions/
```

### 3. Ingest an event

```bash
curl -X POST http://localhost:8000/events/ \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: my-unique-key-123" \
  -d '{
    "event_type": "order.created",
    "payload": {"order_id": 42, "amount": 99.95}
  }'
```

### 4. Check deliveries

```bash
# All deliveries
curl http://localhost:8000/deliveries/

# Filter by status
curl "http://localhost:8000/deliveries/?status=pending"

# Single delivery with attempt logs
curl http://localhost:8000/deliveries/1
```

### 5. Manually retry a failed delivery

```bash
curl -X POST http://localhost:8000/deliveries/1/retry
```

## Testing with the Mock Receiver

Start the mock receiver in a separate terminal — it randomly returns 5xx/429 to test retries:

```bash
python scripts/mock_receiver.py
```

Then create a subscription pointing to `http://localhost:9999/hook` and fire some events.

## Stack

- Python 3.11
- FastAPI
- SQLAlchemy (SQLite)
- httpx
- pytest + pytest-asyncio
