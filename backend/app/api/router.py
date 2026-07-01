from fastapi import APIRouter

from app.api.routes import ai, health, jobs

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(jobs.router)
api_router.include_router(ai.router)
