"""Route modules for the API."""

from app.api.routes.ingredients import router as ingredients_router
from app.api.routes.pantry import router as pantry_router
from app.api.routes.perception import router as perception_router
from app.api.routes.recipes import router as recipes_router

__all__ = ["ingredients_router", "pantry_router", "perception_router", "recipes_router"]
