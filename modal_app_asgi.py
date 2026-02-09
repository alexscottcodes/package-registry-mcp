"""
Modal deployment for Package Registry MCP Server (ASGI version).

This is an alternative deployment approach using ASGI to proxy to the Node.js server.
For most use cases, modal_app.py (using web_server) is simpler.
"""

import asyncio
import os
import subprocess

import modal

# Create a Modal app
app = modal.App("package-registry-mcp-asgi")

# Define the container image with Bun runtime
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("curl", "unzip")
    .pip_install("httpx")
    .run_commands(
        # Install Bun
        "curl -fsSL https://bun.sh/install | bash",
        "ln -s /root/.bun/bin/bun /usr/local/bin/bun",
        # Verify installation
        "bun --version",
    )
    .copy_local_dir("src", "/app/src")
    .copy_local_file("package.json", "/app/package.json")
    .copy_local_file("tsconfig.json", "/app/tsconfig.json")
    .workdir("/app")
    .run_commands(
        # Install dependencies
        "bun install --production",
    )
)


@app.function(
    image=image,
    cpu=1.0,
    memory=512,
    keep_warm=1,
    timeout=300,
)
@modal.asgi_app()
def mcp_server():
    """
    Create an ASGI app that proxies to the Node.js MCP server.
    """
    from fastapi import FastAPI, Request
    from fastapi.responses import StreamingResponse

    web_app = FastAPI(title="Package Registry MCP Server")

    # Server configuration
    server_port = 3000
    server_process = None

    @web_app.on_event("startup")
    async def startup_event():
        """Start the Node.js server on app startup."""
        nonlocal server_process
        server_process = subprocess.Popen(
            ["bun", "run", "/app/src/http-server.ts"],
            env={**os.environ, "PORT": str(server_port)},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Wait for server to start
        await asyncio.sleep(2)

    @web_app.get("/{full_path:path}")
    @web_app.post("/{full_path:path}")
    @web_app.delete("/{full_path:path}")
    async def proxy(full_path: str, request: Request):
        """Proxy all requests to the Node.js server."""
        import httpx

        # Build the target URL
        url = f"http://localhost:{server_port}/{full_path}"

        # Get request details
        method = request.method
        headers = dict(request.headers)
        body = await request.body() if method in ["POST", "DELETE"] else None

        # Forward the request
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method, url=url, headers=headers, content=body, timeout=30.0
            )

            # Check if it's an SSE response
            if response.headers.get("content-type") == "text/event-stream":

                async def event_stream():
                    async for chunk in response.aiter_bytes():
                        yield chunk

                return StreamingResponse(
                    event_stream(),
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type="text/event-stream",
                )
            else:
                # Return regular response
                return StreamingResponse(
                    iter([response.content]),
                    status_code=response.status_code,
                    headers=dict(response.headers),
                )

    return web_app
