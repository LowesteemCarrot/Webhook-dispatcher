"""Event & Webhook Dispatcher Engine – FastAPI application."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine
from app.routers import deliveries, events, subscriptions
from app.worker import worker_loop

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    Base.metadata.create_all(bind=engine)
    # Start the background delivery worker
    task = asyncio.create_task(worker_loop())
    yield
    # Shutdown: cancel the worker
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Event & Webhook Dispatcher Engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(subscriptions.router)
app.include_router(events.router)
app.include_router(deliveries.router)


@app.get("/health")
def health():
    return {"status": "ok"}
