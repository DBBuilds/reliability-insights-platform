"""ASGI app: GraphQL at /graphql, health at /healthz.

Run locally:  uv run uvicorn insights.app:app --reload --port 8000
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from insights.schema import schema
from insights.service import InsightsService
from insights.sources.fixtures import FixtureSource


def build_service() -> InsightsService:
    # Swap FixtureSource for a real connector (or a composite of several) here.
    return InsightsService(FixtureSource())


def create_app(service: InsightsService | None = None) -> FastAPI:
    service = service or build_service()

    async def context() -> dict:
        # Add the authenticated caller here (from your SSO proxy's headers or a
        # verified token), and filter orgs by what they may see.
        return {"service": service}

    app = FastAPI(title="Reliability Insights API")
    origins = [o for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",") if o]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["POST", "GET"], allow_headers=["*"])
    app.include_router(GraphQLRouter(schema, context_getter=context), prefix="/graphql")

    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True}

    return app


app = create_app()
