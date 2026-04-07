"""
Sanctuary Microverse V3.1 — API Server

This is the application shell. All logic lives in:
    - /prompts/       — System prompts and chat management per presence
    - /routes/        — API route handlers per domain
    - cognitive_helpers.py — Shared MRA/Training Arc/Belief Graph pipeline
    - training_arc.py — Phase-based scaffolding system
    - belief_graph.py — Neuronal cognitive architecture (Sleight of Mouth)
    - permanent_mra.py — Long-term canonical memory
    - session_cache_mra.py — Working session memory
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import client

# Import all route modules
from routes.health import router as health_router
from routes.tts import router as tts_router
from routes.sanctuary import router as sanctuary_router
from routes.clarity import router as clarity_router
from routes.resonance import router as resonance_router
from routes.mirror import router as mirror_router
from routes.mra_routes import router as mra_router

# Create the app
app = FastAPI(title="Sanctuary Microverse API")

# Include all routers
app.include_router(health_router)
app.include_router(tts_router)
app.include_router(sanctuary_router)
app.include_router(clarity_router)
app.include_router(resonance_router)
app.include_router(mirror_router)
app.include_router(mra_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
