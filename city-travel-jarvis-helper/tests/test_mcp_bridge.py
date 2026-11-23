import asyncio
from types import SimpleNamespace
import httpx2
import pytest
from fastapi.testclient import TestClient
from fastmcp import Client, FastMCP
from fastmcp.server.providers.openapi import OpenAPIProvider
from app.main import app
from app.mcp_bridge import allowed_user, build_application, curated_spec
from app.mcp_operations import TOOL_OPERATION_IDS

def test_disabled_keeps_legacy_app(monkeypatch):
    monkeypatch.delenv("MCP_ENABLED", raising=False)
    assert build_application(app) is app

def test_enabled_requires_explicit_configuration(monkeypatch):
    monkeypatch.setenv("MCP_ENABLED", "true")
    for key in ("MCP_PUBLIC_BASE_URL", "MCP_GITHUB_CLIENT_ID", "MCP_GITHUB_CLIENT_SECRET", "MCP_ALLOWED_GITHUB_LOGINS", "MCP_JWT_SIGNING_KEY"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(RuntimeError, match="MCP_ENABLED requires"):
        build_application(app)

def test_curated_surface_has_no_credential_arguments():
    spec = curated_spec(app)
    operations = [operation for item in spec["paths"].values() for operation in item.values()]
    assert {operation["operationId"] for operation in operations} == TOOL_OPERATION_IDS
    assert "/health" not in spec["paths"]
    assert all(parameter.get("in") != "header" for operation in operations for parameter in operation.get("parameters", []))

def test_owner_allowlist_is_enforced():
    def context(login):
        return SimpleNamespace(token=SimpleNamespace(claims={"login": login}))
    assert allowed_user(context("Owner"), frozenset({"owner"}))
    assert not allowed_user(context("someone-else"), frozenset({"owner"}))
    assert not allowed_user(SimpleNamespace(token=None), frozenset({"owner"}))

def configure(monkeypatch, tmp_path):
    monkeypatch.setenv("MCP_ENABLED", "true")
    monkeypatch.setenv("MCP_PUBLIC_BASE_URL", "https://jarvis.example")
    monkeypatch.setenv("MCP_GITHUB_CLIENT_ID", "test-client")
    monkeypatch.setenv("MCP_GITHUB_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("MCP_ALLOWED_GITHUB_LOGINS", "owner")
    monkeypatch.setenv("MCP_JWT_SIGNING_KEY", "test-signing-key-with-at-least-32-characters")
    monkeypatch.setenv("ACTION_API_KEY", "test-key")
    monkeypatch.setenv("FASTMCP_HOME", str(tmp_path))

def test_http_requires_auth_and_advertises_oauth(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path)
    application = build_application(app)
    with TestClient(application) as client:
        response = client.post("/mcp-server/mcp", headers={"Accept": "application/json, text/event-stream"}, json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}},
        })
        assert response.status_code == 401
        assert "Bearer" in response.headers["www-authenticate"]
        metadata = client.get("/.well-known/oauth-protected-resource/mcp-server/mcp")
        assert metadata.status_code == 200
        assert metadata.json()["resource"] == "https://jarvis.example/mcp-server/mcp"
        assert client.get("/health").status_code == 200

def test_invalid_public_origin_rejected(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path)
    monkeypatch.setenv("MCP_PUBLIC_BASE_URL", "http://unsafe.example")
    with pytest.raises(RuntimeError, match="HTTPS origin"):
        build_application(app)

def test_tools_are_discoverable_without_credentials_in_schema():
    async def run():
        # Test the adapter against the existing REST app, without external OAuth.
        async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url="http://test") as api_client:
            provider = OpenAPIProvider(curated_spec(app), api_client)
            server = FastMCP("test", providers=[provider])
            async with Client(server) as client:
                tools = await client.list_tools()
                assert {tool.name for tool in tools} == TOOL_OPERATION_IDS
                assert all("authorization" not in tool.input_schema.get("properties", {}) for tool in tools)
                with pytest.raises(Exception):
                    await client.call_tool(next(iter(TOOL_OPERATION_IDS)), {"authorization": "do-not-accept-model-credentials"})
    asyncio.run(run())

def test_production_tools_have_safe_annotations(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path)
    # Simulate an already-authenticated owner; owner rejection is tested separately.
    monkeypatch.setattr('app.mcp_bridge.allowed_user', lambda ctx, logins: True)
    application = build_application(app)
    tools = asyncio.run(application.state.mcp_server.list_tools())
    assert {tool.name for tool in tools} == TOOL_OPERATION_IDS
    for tool in tools:
        assert "authorization" not in tool.parameters.get("properties", {})
        if tool.name.startswith("commit"):
            assert tool.annotations.read_only_hint is False
            assert tool.annotations.destructive_hint is True
        elif tool.name.startswith(("get", "prepare", "executeCityRead")):
            assert tool.annotations.read_only_hint is True

def test_authenticated_owner_can_read_but_not_commit_without_confirmation(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path)
    from app.settings import settings
    monkeypatch.setenv("ACTION_API_KEY", settings.action_api_key)
    monkeypatch.setattr('app.mcp_bridge.allowed_user', lambda ctx, logins: True)
    application = build_application(app)
    async def run():
        async with Client(application.state.mcp_server) as client:
            read_name = next(name for name in ("getFinanceCapabilities", "getFitnessCapabilities", "getCityPluginManifest") if name in TOOL_OPERATION_IDS)
            result = await client.call_tool(read_name, {})
            assert not result.is_error
            if "commitStatementImport" in TOOL_OPERATION_IDS:
                name, args = "commitStatementImport", {"commit_token": "invalid-token-for-test", "confirmed": False}
            elif "commitWorkoutImportByPreviewId" in TOOL_OPERATION_IDS:
                name, args = "commitWorkoutImportByPreviewId", {"preview_id": "INVALID-PREVIEW", "confirmed": False}
            else:
                name, args = "commitCityWriteCapability", {"request_id": "REQ-MCP-TEST", "capability": "city.rule.save", "preview_id": "INVALID-PREVIEW", "confirmed": False}
            with pytest.raises(Exception):
                await client.call_tool(name, args)
    with TestClient(application):
        asyncio.run(run())



