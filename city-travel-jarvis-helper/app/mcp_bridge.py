"""Authenticated MCP adapter. The original REST app remains the source of truth."""
from __future__ import annotations

import copy
import os
from contextlib import asynccontextmanager
from urllib.parse import urlsplit
from typing import Any

from fastapi import FastAPI
from app.mcp_operations import TOOL_OPERATION_IDS, SERVER_NAME

_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}


def curated_spec(api: FastAPI) -> dict[str, Any]:
    spec = copy.deepcopy(api.openapi())
    paths: dict[str, Any] = {}
    found: set[str] = set()
    for path, item in spec.get("paths", {}).items():
        selected = {}
        for method, operation in item.items():
            if method.lower() not in _METHODS or not isinstance(operation, dict):
                continue
            operation_id = operation.get("operationId")
            if operation_id not in TOOL_OPERATION_IDS:
                continue
            # Credentials belong to the server, never to model-generated arguments.
            operation["parameters"] = [
                parameter for parameter in operation.get("parameters", [])
                if parameter.get("in") != "header"
            ]
            operation.pop("security", None)
            operation["description"] = (
                operation.get("description") or operation.get("summary") or operation_id
            )
            if operation_id.startswith("commit"):
                operation["description"] += (
                    " Writes saved data. Call only after showing the preview and receiving "
                    "a separate explicit user confirmation. Existing backend checks apply."
                )
            selected[method] = operation
            found.add(operation_id)
        if selected:
            paths[path] = selected
    missing = TOOL_OPERATION_IDS - found
    if missing:
        raise RuntimeError("MCP operations missing from REST schema: " + ", ".join(sorted(missing)))
    spec["paths"] = paths
    spec.pop("security", None)
    spec.get("components", {}).pop("securitySchemes", None)
    return spec


def allowed_user(ctx: Any, allowed_logins: frozenset[str]) -> bool:
    if ctx.token is None:
        return False
    return str((ctx.token.claims or {}).get("login", "")).strip().casefold() in allowed_logins


def build_application(api: FastAPI):
    if os.getenv("MCP_ENABLED", "false").strip().lower() not in {"true", "1", "yes", "on"}:
        return api

    required = (
        "MCP_PUBLIC_BASE_URL", "MCP_GITHUB_CLIENT_ID", "MCP_GITHUB_CLIENT_SECRET",
        "MCP_ALLOWED_GITHUB_LOGINS", "MCP_JWT_SIGNING_KEY", "ACTION_API_KEY",
    )
    missing = [name for name in required if not os.getenv(name, "").strip()]
    if missing:
        raise RuntimeError("MCP_ENABLED requires: " + ", ".join(missing))
    base_url = os.environ["MCP_PUBLIC_BASE_URL"].strip().rstrip("/")
    parsed = urlsplit(base_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username:
        raise RuntimeError("MCP_PUBLIC_BASE_URL must be an HTTPS origin without path or credentials")
    if len(os.environ["MCP_JWT_SIGNING_KEY"].strip()) < 32:
        raise RuntimeError("MCP_JWT_SIGNING_KEY must contain at least 32 characters")
    logins = frozenset(value.strip().casefold() for value in os.environ["MCP_ALLOWED_GITHUB_LOGINS"].split(",") if value.strip())
    if not logins:
        raise RuntimeError("MCP_ALLOWED_GITHUB_LOGINS must contain an owner login")

    import httpx2
    from fastmcp import FastMCP
    from fastmcp.server.auth.providers.github import GitHubProvider
    from fastmcp.server.middleware import AuthMiddleware
    from fastmcp.server.providers.openapi import OpenAPIProvider
    from mcp.types import ToolAnnotations
    from starlette.applications import Starlette
    from starlette.routing import Mount

    action_key = os.environ["ACTION_API_KEY"].strip()

    class InternalTransport(httpx2.ASGITransport):
        async def handle_async_request(self, request):
            # Do not forward client cookies or credentials to the REST app.
            content_type = request.headers.get("content-type", "application/json")
            request.headers.clear()
            request.headers.update({
                "host": "jarvis.internal",
                "content-type": content_type,
                "authorization": f"Bearer {action_key}",
            })
            return await super().handle_async_request(request)

    internal_client = httpx2.AsyncClient(
        transport=InternalTransport(app=api),
        base_url="http://jarvis.internal", timeout=60.0,
    )

    def customize(route, component):
        name = route.operation_id or ""
        read_only = route.method.upper() == "GET" or name.startswith(("get", "prepare", "executeCityRead"))
        component.annotations = ToolAnnotations(
            readOnlyHint=read_only,
            destructiveHint=name.startswith("commit"),
            idempotentHint=read_only,
            openWorldHint=True,
        )

    provider = OpenAPIProvider(curated_spec(api), internal_client, mcp_component_fn=customize)
    auth = GitHubProvider(
        client_id=os.environ["MCP_GITHUB_CLIENT_ID"].strip(),
        client_secret=os.environ["MCP_GITHUB_CLIENT_SECRET"].strip(),
        base_url=f"{base_url}/mcp-server",
        jwt_signing_key=os.environ["MCP_JWT_SIGNING_KEY"].strip(),
    )
    mcp = FastMCP(
        SERVER_NAME, auth=auth, providers=[provider],
        middleware=[AuthMiddleware(auth=lambda ctx: allowed_user(ctx, logins))],
    )
    mcp_http = mcp.http_app(path="/mcp", stateless_http=True)

    @asynccontextmanager
    async def lifespan(application):
        try:
            async with mcp_http.lifespan(application):
                yield
        finally:
            await internal_client.aclose()

    application = Starlette(
        routes=[
            *auth.get_well_known_routes(mcp_path="/mcp"),
            Mount("/mcp-server", app=mcp_http),
            Mount("/", app=api),
        ],
        lifespan=lifespan,
    )
    application.state.mcp_server = mcp
    return application

