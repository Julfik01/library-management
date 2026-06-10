# backend/app/main.py
# FastAPI application entry point.
# CRITICAL: CORS must use explicit origin list — never allow_origins=["*"] with allow_credentials=True.
# Browsers block credentialed requests (withCredentials/httpOnly cookie) to wildcard origins.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    """Health check endpoint — observable before auth exists."""
    return {"status": "ok"}


# Routers are wired in plan 02 (auth endpoints)
