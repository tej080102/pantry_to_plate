"""Route modules for the API."""

from app.api.routes.ingredients import router as ingredients_router
from app.api.routes.recipes import router as recipes_router

__all__ = ["ingredients_router", "recipes_router"]
