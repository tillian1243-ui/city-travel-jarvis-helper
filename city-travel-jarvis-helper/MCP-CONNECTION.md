# City & Travel Jarvis: authenticated MCP connection

The existing REST API remains available. MCP is disabled unless `MCP_ENABLED=true`.
This adapter exposes only the explicitly reviewed operation IDs in
`app/mcp_operations.py`; health, hidden legacy routes and future routes are excluded.
All calls use the existing validation, storage and preview/confirmation checks.

## Railway configuration

Deploy this change in the existing Railway service, preserving all current variables,
volumes, Google connections and write policy. Keep `WRITES_ENABLED` unchanged.

Create an owner-controlled GitHub OAuth App with:
- Homepage: https://fearless-friendship-production-1929.up.railway.app
- Authorization callback: https://fearless-friendship-production-1929.up.railway.app/mcp-server/auth/callback

Configure in Railway (do not put secrets in a plugin, repository or chat):
- `MCP_ENABLED=true`
- `MCP_PUBLIC_BASE_URL=https://fearless-friendship-production-1929.up.railway.app`
- `MCP_GITHUB_CLIENT_ID` and `MCP_GITHUB_CLIENT_SECRET`: from that OAuth App
- `MCP_ALLOWED_GITHUB_LOGINS=tillian1243-ui`
- `MCP_JWT_SIGNING_KEY`: a private random value of at least 32 characters, retained across deployments
- Existing `ACTION_API_KEY`: retain the current nonempty value.

Use a separate OAuth App per service because each service has its own callback.
Persist FastMCP's encrypted OAuth storage on the service's existing persistent volume
when available; without persistent storage, redeployment can require reconnecting.
Never disable authentication to resolve a failed connection.

## Connect in ordinary ChatGPT

Only after deployment and verification, add a custom MCP server with:
- Name: City & Travel Jarvis
- URL: https://fearless-friendship-production-1929.up.railway.app/mcp-server/mcp
- Authentication: OAuth

Complete sign-in as the allowlisted owner. Discovery must list the expected operations.
A public `401` on the MCP endpoint is expected before login; public OAuth metadata
and the original `/health` must remain reachable.

Migrate the original GPT's instructions and knowledge only after backing up Actions.
The platform's GPT-to-plugin migration does not preserve Actions and prevents further
editing of the original GPT. The MCP connection is a separate step; a successful
instruction import does not demonstrate working tools. Reuse the resulting plugin
instead of generating duplicate skill-only plugins.

Do not silently substitute a repository instruction version for a newer GPT upload.
Verify attachment import and generated artifacts separately in ChatGPT: former
GPT-specific file references are not proof of plugin attachment support.

## Validation

Run from the service root with Python 3.12:
```sh
python -m pip install -r requirements.txt
python -m pytest -q
```

City also needs `requirements-dev.txt` for its test runner.
Tests use in-memory fixtures, not the owner's Google Sheets.
They verify legacy functions, exact tool discovery, hidden credential arguments,
owner allowlisting, unauthenticated HTTP rejection, OAuth discovery and rejection of
unconfirmed writes through the actual MCP-to-REST adapter.

After configuration, verify one authenticated read from ChatGPT. Do not use a real
write to test connectivity. Deployment, OAuth consent, file attachment parity and
end-to-end ChatGPT behavior remain unverified until this checklist is completed.

Rollback: set `MCP_ENABLED=false` and redeploy to retain the legacy REST application.

