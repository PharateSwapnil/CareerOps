from fastapi import APIRouter

from app.api.routes import (
    ai,
    applications,
    auth,
    automation,
    companies,
    contacts,
    health,
    jobs,
    profile,
    resumes,
    saved_searches,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(jobs.router)
api_router.include_router(ai.router)
api_router.include_router(applications.router)
api_router.include_router(resumes.router)
api_router.include_router(saved_searches.router)
api_router.include_router(contacts.router)
api_router.include_router(companies.router)
api_router.include_router(profile.router)
api_router.include_router(automation.router)
