# Modal Deployment Guide

This guide explains how to deploy the Package Registry MCP Server to Modal.com
with a public HTTP endpoint.

## Prerequisites

1. **Modal Account**: Sign up at [modal.com](https://modal.com)
2. **Modal CLI**: Install and authenticate
   ```bash
   pip install modal
   modal setup
   ```

## Deployment Architecture

The deployment consists of:

- **Python wrapper** (`modal_app.py`): Modal application that manages the
  container
- **Node.js HTTP server** (`src/http-server.ts`): Express server with Streamable
  HTTP transport
- **MCP tools**: All existing package registry tools

The server uses the Streamable HTTP transport protocol, which is the modern
standard for remote MCP servers (replacing the deprecated SSE transport).

## Deployment Options

This repository includes two Modal deployment approaches:

1. **`modal_app.py`** (Recommended): Uses Modal's `@modal.web_server` decorator
   for simpler deployment
2. **`modal_app_asgi.py`**: Uses `@modal.asgi_app` with FastAPI proxy for more
   control

Both approaches work identically from the client's perspective. Choose based on
your preference.

## Quick Start

### 1. Deploy to Modal

**Option A: Simple web server (recommended)**

```bash
modal deploy modal_app.py
```

This command will:

- Build a container with Bun runtime
- Install dependencies
- Deploy the MCP server
- Provide you with a public HTTPS URL

Example output:

```
✓ Created package-registry-mcp::mcp_server
✓ App deployed!

View live logs: https://modal.com/apps/your-workspace/package-registry-mcp
MCP endpoint: https://your-workspace--package-registry-mcp-mcp-server.modal.run/mcp
```

### 2. Test the Deployment

#### Check server status

```bash
curl https://your-workspace--package-registry-mcp-mcp-server.modal.run/
```

Expected response:

```json
{
  "name": "package-registry-mcp",
  "version": "2.1.0",
  "description": "MCP server for searching and getting up-to-date information about NPM, Cargo, NuGet, PyPI, and Go packages.",
  "endpoints": {
    "mcp": "/mcp",
    "health": "/health"
  },
  "transport": "streamable-http"
}
```

#### Health check

```bash
curl https://your-workspace--package-registry-mcp-mcp-server.modal.run/health
```

### 3. Connect from MCP Client

The deployed server can be accessed by any MCP client that supports Streamable
HTTP transport.

#### Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "package-registry": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://your-workspace--package-registry-mcp-mcp-server.modal.run/mcp"
      ]
    }
  }
}
```

#### Programmatic Access (TypeScript)

```typescript
import { Client } from '@modelcontextprotocol/sdk/client/index.js'
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js'

const transport = new StreamableHTTPClientTransport({
  url: 'https://your-workspace--package-registry-mcp-mcp-server.modal.run/mcp'
})

const client = new Client({
  name: 'my-client',
  version: '1.0.0'
})

await client.connect(transport)

// List available tools
const tools = await client.listTools()
console.log(tools)

// Call a tool
const result = await client.callTool({
  name: 'search-npm-packages',
  arguments: { query: 'react' }
})
```

#### Programmatic Access (Python)

```python
from mcp import ClientSession, StreamableHTTPTransport

transport = StreamableHTTPTransport(
    url="https://your-workspace--package-registry-mcp-mcp-server.modal.run/mcp"
)

async with ClientSession(transport) as session:
    # List available tools
    tools = await session.list_tools()
    print(tools)

    # Call a tool
    result = await session.call_tool(
        "search-npm-packages",
        arguments={"query": "react"}
    )
```

## Local Development

### Run HTTP Server Locally

```bash
bun run http
```

The server will start at `http://localhost:3000/mcp`

### Test with MCP Inspector

```bash
# Install MCP inspector
npx @modelcontextprotocol/inspector

# Run your local server
bun run http

# In another terminal, connect the inspector
npx @modelcontextprotocol/inspector http://localhost:3000/mcp
```

## Configuration

### Environment Variables

You can configure the Modal deployment by setting environment variables in
`modal_app.py`:

- `PORT`: HTTP server port (default: 3000)

### Resource Allocation

Modify the `@app.function()` decorator in `modal_app.py`:

```python
@app.function(
    image=image,
    cpu=2.0,        # Increase CPU
    memory=1024,    # Increase memory (MB)
    keep_warm=2,    # Keep multiple instances warm
    timeout=600,    # Increase timeout (seconds)
)
```

### Cold Start Optimization

The deployment uses `keep_warm=1` by default to maintain one warm container,
reducing cold start latency. Adjust based on your traffic patterns:

- `keep_warm=0`: No warm containers (cost-effective for low traffic)
- `keep_warm=1`: One warm container (balanced)
- `keep_warm=2+`: Multiple warm containers (low latency for high traffic)

## Available Tools

The deployed server exposes the following MCP tools:

### NPM

- `search-npm-packages`: Search for NPM packages
- `get-npm-package-details`: Get details about an NPM package
- `list-npm-package-versions`: List versions of an NPM package

### Cargo (Rust)

- `search-cargo-packages`: Search for Cargo packages
- `get-cargo-package-details`: Get details about a Cargo package
- `list-cargo-package-versions`: List versions of a Cargo package

### NuGet (.NET)

- `search-nuget-packages`: Search for NuGet packages
- `get-nuget-package-details`: Get details about a NuGet package
- `list-nuget-package-versions`: List versions of a NuGet package

### PyPI (Python)

- `get-pypi-package-details`: Get details about a PyPI package
- `list-pypi-package-versions`: List versions of a PyPI package

### Go Modules

- `get-golang-package-details`: Get details about a Go module
- `list-golang-package-versions`: List versions of a Go module

### GitHub Security Advisories

- `search-github-advisories`: Search GitHub security advisories
- `get-github-advisory-details`: Get details about a security advisory
- `get-github-package-advisories`: Get security advisories for a specific
  package

## Monitoring

### View Logs

```bash
modal app logs package-registry-mcp
```

### View Dashboard

Visit your Modal dashboard to see:

- Request metrics
- Container status
- Error logs
- Resource usage

Dashboard URL will be shown after deployment.

## Troubleshooting

### Server Not Responding

Check the logs:

```bash
modal app logs package-registry-mcp
```

### Cold Start Issues

If you experience slow initial requests:

1. Increase `keep_warm` value
2. Check the Modal dashboard for container startup times

### Connection Errors

1. Verify the URL is correct
2. Check firewall/network settings
3. Ensure the client supports Streamable HTTP transport

## Updating the Deployment

To update the deployed server:

```bash
modal deploy modal_app.py
```

Modal will perform a rolling update with zero downtime.

## Stopping the Deployment

```bash
modal app stop package-registry-mcp
```

## Cost Optimization

- Use `keep_warm=0` for development
- Set appropriate `timeout` values
- Monitor usage in Modal dashboard
- Consider using Modal's autoscaling features

## Security Considerations

- The server disables DNS rebinding protection to allow public access
- Consider adding authentication for production use
- Use HTTPS (provided by Modal automatically)
- Monitor access logs for suspicious activity

## Additional Resources

- [Modal Documentation](https://modal.com/docs)
- [MCP Specification](https://modelcontextprotocol.info/)
- [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)
- [Streamable HTTP Transport](https://modelcontextprotocol.info/docs/concepts/transports/)
