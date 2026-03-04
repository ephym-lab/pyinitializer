"""
Python Initializr — FastAPI application entry point.

Startup:
  - Loads the full PyPI Simple Index into memory for package search.

CORS:
  - Configured for local Next.js development (http://localhost:3000).
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import generate, preview, search
from services import pypi_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)



# Lifespan — load PyPI index on startup


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Python Initializer backend …")
    # Non-blocking: we fire-and-forget so the server starts immediately.
    # The search endpoint will return empty results until loading is done.
    import asyncio
    asyncio.create_task(pypi_service.load_index())
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

# CORS — allow local Next.js frontend and any deployed frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Venv-Excluded", "Content-Disposition"],
)


# Routers

app.include_router(generate.router)
app.include_router(preview.router)
app.include_router(search.router)


# Root health check

@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Python Initializr API",
        "version": "0.1.0",
        "docs": "/docs",
        "pypi_index_loaded": pypi_service.is_loaded(),
    }


@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "ok",
        "pypi_index_loaded": pypi_service.is_loaded(),
    }
