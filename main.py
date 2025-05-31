"""
Data Processing Pipeline System - Main Application Entry Point
FastAPI-based system for managing and executing configurable data workflows
"""

import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from contextlib import asynccontextmanager

from app.routers import pipelines, executions, files, api_sources, triggers
from app.utils.logger import setup_logging
from app.scheduler import PipelineScheduler
from config import settings


# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global scheduler
    
    # Startup
    logger.info("Starting Data Processing Pipeline System")
    
    # Initialize scheduler
    scheduler = PipelineScheduler()
    await scheduler.start()
    
    # Create necessary directories
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Data Processing Pipeline System")
    if scheduler:
        await scheduler.stop()


# Create FastAPI application
app = FastAPI(
    title="Data Processing Pipeline System",
    description="A comprehensive system for managing and executing configurable data workflows",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(pipelines.router, prefix="/api/v1", tags=["Pipelines"])
app.include_router(executions.router, prefix="/api/v1", tags=["Executions"])
app.include_router(files.router, prefix="/api/v1", tags=["Files"])
app.include_router(api_sources.router, prefix="/api/v1", tags=["API Sources"])
app.include_router(triggers.router, prefix="/api/v1", tags=["Triggers"])

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """Serve the main application page"""
    return FileResponse("static/index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Data Processing Pipeline System",
        "version": "1.0.0"
    }


@app.get("/api/v1/scheduler/status")
async def get_scheduler_status():
    """Get scheduler status"""
    global scheduler
    if scheduler:
        return {
            "status": "running" if scheduler.running else "stopped",
            "scheduled_jobs": len(scheduler.jobs)
        }
    return {"status": "not_initialized", "scheduled_jobs": 0}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info"
    )
