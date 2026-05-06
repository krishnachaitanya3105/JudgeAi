"""
JudgeAI — FastAPI Application Entry Point
──────────────────────────────────────────────────
Legal governance assistant powered by Groq LLaMA3
with Supabase storage and structured data extraction.
"""

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from backend.routers import upload, extract, verification, dashboard, batch_upload, demo_router, search_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from backend.services.notification_scheduler import shutdown_scheduler, start_scheduler

    start_scheduler()
    try:
        yield
    finally:
        shutdown_scheduler()


# ── Application Instance ─────────────────────────
app = FastAPI(
    title="JudgeAI",
    description="AI-powered legal governance assistant for court judgment analysis",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS (dev + configurable prod) ─
#
# Env:
# - CORS_ALLOW_ORIGINS="https://your-frontend.vercel.app,https://yourdomain.com"
# - CORS_ALLOW_ORIGIN_REGEX="https://.*\\.vercel\\.app"
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
    r"http://(localhost|127\.0\.0\.1):\d+|https://.*\.vercel\.app",
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

# ── Register Routers ────────────────────────────
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(batch_upload.router, prefix="/api", tags=["Upload"])
app.include_router(extract.router, prefix="/api", tags=["Extraction"])
app.include_router(demo_router.router, prefix="/api", tags=["Demo"])
app.include_router(verification.router, prefix="/api", tags=["Verification"])
app.include_router(dashboard.router, prefix="/api", tags=["Dashboards"])
app.include_router(search_router.router, prefix="/api", tags=["Search"])


# ── Health Check ─────────────────────────────────
@app.get("/", tags=["Health"])
async def health_check():
    return {
        "status": "operational",
        "service": "JudgeAI API",
        "version": "2.0.0",
    }
