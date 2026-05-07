"""
JudgeAI — FastAPI Application Entry Point
──────────────────────────────────────────────────
Legal governance assistant powered by Groq LLaMA3
with Supabase storage and structured data extraction.
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.gzip import GZipMiddleware

# ── Structured logging ────────────────────────────────────────
_log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, _log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
_logger = logging.getLogger("judgeai.main")

from backend.routers import (
    batch_upload,
    dashboard,
    demo_router,
    extract,
    search_router,
    upload,
    verification,
)

APP_VERSION = "2.1.0"
_START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from backend.services.notification_scheduler import shutdown_scheduler, start_scheduler

    _logger.info("JudgeAI v%s starting up (log_level=%s)…", APP_VERSION, _log_level)
    start_scheduler()
    try:
        yield
    finally:
        _logger.info("JudgeAI shutting down…")
        shutdown_scheduler()


# ── Application Instance ──────────────────────────────────────
app = FastAPI(
    title="JudgeAI",
    description="AI-powered legal governance assistant for court judgment analysis",
    version=APP_VERSION,
    docs_url="/docs",
    openapi_url="/openapi.json",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ── Global exception handler — always returns JSON ────────────
@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception):
    _logger.error(
        "Unhandled exception on %s %s: %s",
        request.method, request.url.path, exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "path": request.url.path,
        },
    )


# ── CORS ───────────────────────────────────────────────────────
cors_allow_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
extra = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
if extra:
    cors_allow_origins.extend([o.strip() for o in extra.split(",") if o.strip()])

cors_allow_origin_regex = os.getenv(
    "CORS_ALLOW_ORIGIN_REGEX",
    r"http://(localhost|127\.0\.0\.1):\d+|https://[a-zA-Z0-9-]+\.vercel\.app|https://judgeai.*\.vercel\.app",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins,
    allow_origin_regex=cors_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=500)


# ── Routers ────────────────────────────────────────────────────
app.include_router(upload.router,         prefix="/api", tags=["Upload"])
app.include_router(batch_upload.router,   prefix="/api", tags=["Upload"])
app.include_router(extract.router,        prefix="/api", tags=["Extraction"])
app.include_router(demo_router.router,    prefix="/api", tags=["Demo"])
app.include_router(verification.router,   prefix="/api", tags=["Verification"])
app.include_router(dashboard.router,      prefix="/api", tags=["Dashboards"])
app.include_router(search_router.router,  prefix="/api", tags=["Search"])


# ── Health check (with DB ping) ───────────────────────────────
@app.get("/", tags=["Health"])
async def health_check():
    """Primary health endpoint. Returns quickly even if DB is slow."""
    import asyncio
    
    uptime_sec = round(time.time() - _START_TIME, 1)
    db_ok = False
    db_error = None
    
    try:
        # Use asyncio timeout to prevent hanging on DB issues
        from backend.config import get_supabase
        
        async def check_db():
            """Non-blocking DB check wrapped in timeout."""
            try:
                get_supabase().table("cases").select("id").limit(1).execute()
                return True, None
            except Exception as e:
                return False, str(e)[:200]
        
        db_ok, db_error = await asyncio.wait_for(
            asyncio.to_thread(check_db), timeout=5.0
        )
    except asyncio.TimeoutError:
        _logger.warning("Health check DB ping timeout (>5s)")
        db_error = "DB check timeout"
    except Exception as e:
        _logger.warning("Health check DB ping failed: %s", e)
        db_error = str(e)[:200]

    return {
        "status": "operational" if db_ok else "degraded",
        "service": "JudgeAI API",
        "version": APP_VERSION,
        "uptime_sec": uptime_sec,
        "db": "ok" if db_ok else ("unreachable" if db_error else "unknown"),
        "db_error": db_error,
    }


@app.get("/health", tags=["Health"])
async def health_detail():
    """Render health check endpoint — returns 200 unless completely broken."""
    return await health_check()
