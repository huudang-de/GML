"""FastAPI application package initialization.

Specifications:
- Re-exports create_app and app from app.api.main
"""

from app.api.main import create_app, app

__all__ = ["create_app", "app"]
