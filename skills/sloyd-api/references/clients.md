# Connecting other MCP clients

The server is `https://api.sloyd.ai/api/mcp` (Streamable HTTP). Send the key as the `x-client-id` and `x-client-secret` headers. Clients that can only send a token can use `Authorization: Bearer <clientId>:<clientSecret>`. Keep the secret in an environment variable or the client's secret store, never in a shared config file.

## Cursor

`~/.cursor/mcp.json`, or `.cursor/mcp.json` in the project (keep it git-ignored):

```json
{
  "mcpServers": {
    "sloyd": {
      "url": "https://api.sloyd.ai/api/mcp",
      "headers": { "x-client-id": "${env:SLOYD_CLIENT_ID}", "x-client-secret": "${env:SLOYD_CLIENT_SECRET}" }
    }
  }
}
```

## VS Code

`.vscode/mcp.json`. VS Code asks for the secret once and stores it securely:

```json
{
  "inputs": [{ "type": "promptString", "id": "sloyd-client-secret", "description": "Sloyd API client secret", "password": true }],
  "servers": {
    "sloyd": {
      "type": "http",
      "url": "https://api.sloyd.ai/api/mcp",
      "headers": { "x-client-id": "${env:SLOYD_CLIENT_ID}", "x-client-secret": "${input:sloyd-client-secret}" }
    }
  }
}
```

## Clients that only run local (stdio) servers

Claude Desktop's config file, for example. Bridge with `mcp-remote`:

```json
{
  "mcpServers": {
    "sloyd": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://api.sloyd.ai/api/mcp", "--header", "Authorization:${SLOYD_AUTH}"],
      "env": { "SLOYD_AUTH": "Bearer <clientId>:<clientSecret>" }
    }
  }
}
```

claude.ai and ChatGPT connectors that need OAuth sign-in aren't supported yet.

## Skills without a plugin

`npx skills add Sloydai/roblox-studio-team --all` installs the skills for most agents (Claude Code, Codex, Cursor, opencode, Kiro, GitHub Copilot). The commands in the skills use `<skills>`, which means the folder they were installed into. No MCP server is needed: `sloyd-api/scripts/sloyd.py tool <name> '<json>'` calls the same tools over plain HTTPS.
