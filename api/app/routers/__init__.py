"""Routers package."""
from api.app.routers.health import router as health_router
from api.app.routers.jobs import router as jobs_router
from api.app.routers.search import router as search_router
from api.app.routers.stats import router as stats_router

__all__ = [
    "health_router",
    "jobs_router",
    "stats_router",
    "search_router",
]
