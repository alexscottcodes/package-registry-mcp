"""
Modal deployment for Package Registry MCP Server.

This module deploys the MCP server on Modal.com with a public HTTP endpoint.
The server uses Streamable HTTP transport to enable remote MCP connections.
"""

import modal

# Create a Modal app
app = modal.App("package-registry-mcp")

# Define the container image with Node.js runtime
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("curl", "nodejs", "npm", "git", "zip", "unzip")
    .run_commands(
        # Install Node.js 22.x (required by the project)
        "curl -fsSL https://deb.nodesource.com/setup_22.x | bash -",
        "apt-get install -y nodejs",
        # Verify installation
        "node --version",
        "npm --version",
    )
    .add_local_dir("src", "/app/src", copy=True)
    .add_local_file("package.json", "/app/package.json", copy=True)
    .add_local_file("bun.lock", "/app/bun.lock", copy=True)
    .workdir("/app")
    .run_commands(
        # Install Bun for building
        "curl -fsSL https://bun.sh/install | bash",
        "export PATH=\"/root/.bun/bin:$PATH\"",
        "ln -sf /root/.bun/bin/bun /usr/local/bin/bun",
        # Verify Bun installation
        "bun --version",
        # Install all dependencies (including devDependencies for building)
        "bun install",
        # Build the project
        "bun run build",
        # Verify the build output
        "ls -la /app/dist/",
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

    # Start the Node.js server
    subprocess.Popen(
        ["node", "/app/dist/http-server.js"],
        env={"PORT": "3000"},
    )
