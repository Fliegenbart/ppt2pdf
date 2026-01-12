"""
Vercel Serverless Function Handler for FastAPI
"""
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

# Import routes from backend
from api.routes import router
from api.models import *

# Create FastAPI app for Vercel
app = FastAPI(
    title="PPTX to Accessible PDF Converter",
    description="AI-powered tool to convert PowerPoint presentations to fully accessible PDFs",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "pptx2pdf-accessible"}


# Vercel handler
handler = Mangum(app, lifespan="off")
