"""
PayFlow AI - FastAPI Application

Main app instance with CORS, routing, and lifecycle events.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import chat, system
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PayFlow AI API",
    description="Conversational Analytics Engine for Digital Payments",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(chat.router)
app.include_router(system.router)


@app.on_event("startup")
async def startup_event():
    logger.info("🚀 PayFlow AI API starting up...")
    logger.info(f"📊 Dataset: {settings.DATA_PATH}")
    logger.info(f"🧠 Hypotheses: {settings.HYPOTHESIS_PATH}")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("👋 PayFlow AI API shutting down...")


@app.get("/")
async def root():
    return {
        "message": "PayFlow AI API",
        "version": "1.0.0",
        "docs": "/docs",
    }
