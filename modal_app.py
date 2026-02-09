"""
Modal deployment for Package Registry MCP Server.

This module deploys the MCP server on Modal.com with a public HTTP endpoint.
The server uses Streamable HTTP transport to enable remote MCP connections.
"""

import modal

# Create a Modal app
app = modal.App("package-registry-mcp")

# Define the container image with Bun runtime
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("curl", "unzip")
    .run_commands(
        # Install Bun
        "curl -fsSL https://bun.sh/install | bash",
        "ln -s /root/.bun/bin/bun /usr/local/bin/bun",
        # Verify installation
        "bun --version",
    )
    .add_local_dir("src", "/app/src")
    .add_local_file("package.json", "/app/package.json")
    .add_local_file("tsconfig.json", "/app/tsconfig.json")
    .workdir("/app")
    .run_commands(
        # Install dependencies
        "bun install --production",
    )
)


@app.function(
    image=image,
    # Use CPU-only instance
    cpu=1.0,
    memory=512,
    # Keep warm to reduce cold starts
    keep_warm=1,
    # Set timeout
    timeout=300,
)
@modal.web_server(3000)
def mcp_server():
    """
    Start the MCP HTTP server.

    This function starts the Node.js MCP server with Streamable HTTP transport
    and exposes it as a Modal web endpoint on port 3000.
    """
    import subprocess

    # Start the Bun server
    subprocess.Popen(
        ["bun", "run", "/app/src/http-server.ts"],
        env={"PORT": "3000"},
    )
