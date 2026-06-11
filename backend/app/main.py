# backend/app/main.py
# FastAPI application entry point.
# CRITICAL: CORS must use explicit origin list — never allow_origins=["*"] with allow_credentials=True.
# Browsers block credentialed requests (withCredentials/httpOnly cookie) to wildcard origins.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, admin
from app.routers import borrow_requests, loans

app = FastAPI(
    title="University Library Management System",
    version="1.0.0",
    description="Library management system for university students and librarians.",
)

# CRITICAL: Never use allow_origins=["*"] with allow_credentials=True.
# Browsers block credentialed requests to wildcard origins (CLAUDE.md constraint).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # explicit origin list only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers — plan 02 auth endpoints
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(borrow_requests.router, prefix="/borrow-requests", tags=["borrow_requests"])
app.include_router(loans.router, prefix="/loans", tags=["loans"])

# APScheduler overdue job wiring
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from app.tasks.overdue_jobs import mark_overdue_once

    scheduler = AsyncIOScheduler()

    @app.on_event("startup")
    async def start_scheduler():
        # Run job daily at 00:00 UTC; interval fallback every 24h
        scheduler.add_job(mark_overdue_once, "cron", hour=0, minute=0, id="overdue_job")
        scheduler.start()

    @app.on_event("shutdown")
    async def shutdown_scheduler():
        scheduler.shutdown(wait=False)
except Exception:
    # If APScheduler not installed in dev environment, continue without job
    import logging

    logging.getLogger(__name__).warning("APScheduler not available; overdue job not scheduled")


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    """Health check endpoint — observable before auth exists."""
    return {"status": "ok"}
