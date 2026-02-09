#!/bin/bash

# Test script for the HTTP MCP server

echo "Testing Package Registry MCP HTTP Server"
echo "========================================="
echo

# Server URL
SERVER_URL="${SERVER_URL:-http://localhost:3000}"

echo "1. Testing root endpoint..."
curl -s "$SERVER_URL/" | jq .
echo

echo "2. Testing health endpoint..."
curl -s "$SERVER_URL/health" | jq .
echo

echo "3. Testing MCP endpoint initialization..."
echo "   Note: This requires a proper MCP client for full testing"
echo "   The server is running at: $SERVER_URL/mcp"
echo

echo "To test with the MCP Inspector:"
echo "  npx @modelcontextprotocol/inspector $SERVER_URL/mcp"
echo

echo "To connect from Claude Desktop:"
echo '  Add to claude_desktop_config.json:'
echo '  {'
echo '    "mcpServers": {'
echo '      "package-registry": {'
echo '        "command": "npx",'
echo '        "args": ["-y", "mcp-remote", "'$SERVER_URL'/mcp"]'
echo '      }'
echo '    }'
echo '  }'
