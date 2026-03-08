"""
Python Initializr — FastAPI application entry point.

Startup:
  - Loads the full PyPI Simple Index into memory for package search.

CORS:
  - Configured for local Next.js development (http://localhost:3000).
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from routers import generate, preview, search
from services import pypi_service

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# CORS origins from environment
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")
# Clean up whitespace if any
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS if origin.strip()]



# Lifespan — load PyPI index on startup


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Python Initializer backend …")
    # Non-blocking: we fire-and-forget so the server starts immediately.
    # The search endpoint will return empty results until loading is done.
    import asyncio
    import asyncio
    asyncio.create_task(pypi_service.PyPIService.load_index())
    yield
    logger.info("Shutting down Python Initializr backend.")


# App

app = FastAPI(
    title="Python Initializr API",
    description=(
        "A stateless backend for scaffolding Python projects. "
        "Select your options, download a ZIP or shell-script, and start coding."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow origins from environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Venv-Excluded", "Content-Disposition"],
)


# Routers

# New versioned API for projects
api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(generate.router)
app.include_router(api_v1_router)

# Root-level routes for compatibility with existing frontend
app.include_router(preview.router)
app.include_router(search.router)


# Root health check

@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Python Initializr API",
        "version": "0.1.0",
        "docs": "/docs",
        "pypi_index_loaded": pypi_service.PyPIService.is_loaded(),
    }


@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "ok",
        "pypi_index_loaded": pypi_service.is_loaded(),
    }
