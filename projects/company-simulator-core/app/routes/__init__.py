"""API route registration.

Usage in main.py:
    from app.routes import register_routers
    register_routers(app)
"""

from fastapi import FastAPI


def register_routers(app: FastAPI) -> None:
    """Import and include all route modules."""
    from app.routes.health import router as health_router

    app.include_router(health_router)
