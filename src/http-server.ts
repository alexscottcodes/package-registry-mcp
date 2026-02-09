#!/usr/bin/env node

import express from 'express'
import type { Request, Response } from 'express'
import { randomUUID } from 'node:crypto'

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js'
import { isInitializeRequest } from '@modelcontextprotocol/sdk/types.js'

// Import all tools to register them
import './tools/cargo-details'
import './tools/cargo-search'
import './tools/cargo-versions'
import './tools/github-advisories-details'
import './tools/github-advisories-search'
import './tools/github-package-advisories'
import './tools/golang-details'
import './tools/golang-versions'
import './tools/npm-details'
import './tools/npm-search'
import './tools/npm-versions'
import './tools/nuget-details'
import './tools/nuget-search'
import './tools/nuget-versions'
import './tools/pypi-details'
import './tools/pypi-versions'
import { server as mcpServer } from './server'

const app = express()
app.use(express.json())

// Map to store transports by session ID
const transports: { [sessionId: string]: StreamableHTTPServerTransport } = {}

// Function to create a new MCP server instance
function getServer(): McpServer {
  return mcpServer
}

// Root endpoint with server information
app.get('/', (req: Request, res: Response) => {
  res.json({
    name: 'package-registry-mcp',
    version: '2.1.0',
    description:
      'MCP server for searching and getting up-to-date information about NPM, Cargo, NuGet, PyPI, and Go packages.',
    endpoints: {
      mcp: '/mcp',
      health: '/health'
    },
    transport: 'streamable-http'
  })
})

// Health check endpoint
app.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'ok' })
})

// Handle POST requests for client-to-server communication
app.post('/mcp', async (req: Request, res: Response) => {
  // Check for existing session ID
  const sessionId = req.headers['mcp-session-id'] as string | undefined
  let transport: StreamableHTTPServerTransport

  if (sessionId && transports[sessionId]) {
    // Reuse existing transport
    transport = transports[sessionId]
  } else if (!sessionId && isInitializeRequest(req.body)) {
    // New initialization request
    transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: () => randomUUID(),
      // Disable DNS rebinding protection for public deployment
      enableDnsRebindingProtection: false
    })

    // Store transport for this session
    const newSessionId = transport.sessionId
    if (newSessionId) {
      transports[newSessionId] = transport
    }

    // Connect server to transport
    await getServer().connect(transport)
  } else {
    // Invalid request
    res.status(400).json({
      error: 'Invalid request',
      message: 'Missing session ID or not an initialize request'
    })
    return
  }

  // Handle the request
  try {
    await transport.handleRequest(req, res)
  } catch (error) {
    console.error('Error handling MCP request:', error)
    if (!res.headersSent) {
      res.status(500).json({
        error: 'Internal server error',
        message: error instanceof Error ? error.message : 'Unknown error'
      })
    }
  }
})

// Handle GET requests for server-to-client SSE streams
app.get('/mcp', async (req: Request, res: Response) => {
  const sessionId = req.headers['mcp-session-id'] as string | undefined

  if (!sessionId || !transports[sessionId]) {
    res.status(400).json({
      error: 'Invalid request',
      message: 'Missing or invalid session ID'
    })
    return
  }

  const transport = transports[sessionId]

  try {
    await transport.handleRequest(req, res)
  } catch (error) {
    console.error('Error handling SSE request:', error)
    if (!res.headersSent) {
      res.status(500).json({
        error: 'Internal server error',
        message: error instanceof Error ? error.message : 'Unknown error'
      })
    }
  }
})

// Handle DELETE requests to end sessions
app.delete('/mcp', async (req: Request, res: Response) => {
  const sessionId = req.headers['mcp-session-id'] as string | undefined

  if (sessionId && transports[sessionId]) {
    const transport = transports[sessionId]

    try {
      await transport.handleRequest(req, res)
      // Clean up transport
      delete transports[sessionId]
    } catch (error) {
      console.error('Error handling DELETE request:', error)
      if (!res.headersSent) {
        res.status(500).json({
          error: 'Internal server error',
          message: error instanceof Error ? error.message : 'Unknown error'
        })
      }
    }
  } else {
    res.status(404).json({
      error: 'Session not found',
      message: 'No active session with the provided ID'
    })
  }
})

// Start the server
const PORT = process.env.PORT || 3000
app.listen(PORT, () => {
  console.error(`Package Registry MCP Server running on HTTP port ${PORT}`)
  console.error(`MCP endpoint: http://localhost:${PORT}/mcp`)
})
