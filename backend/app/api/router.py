from fastapi import APIRouter

from app.api.routes import ai, applications, contacts, health, jobs, resumes, saved_searches

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(jobs.router)
api_router.include_router(ai.router)
api_router.include_router(applications.router)
api_router.include_router(resumes.router)
api_router.include_router(saved_searches.router)
api_router.include_router(contacts.router)
