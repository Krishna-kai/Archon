# Archon MCP Integration Guide

## Overview

Archon's MCP (Model Context Protocol) server allows you to connect AI assistants like Claude Desktop, Cursor, and other MCP-compatible tools to your knowledge base and project management system.

## Current Deployment Status

✅ **Successfully Deployed with Supabase Pro**

Your Archon instance is running with the following services:

| Service | URL | Status | Purpose |
|---------|-----|--------|---------|
| **Web UI** | http://localhost:9737 | ✅ Running | Knowledge management interface |
| **API Server** | http://localhost:9181 | ✅ Running | Core business logic and data processing |
| **MCP Server** | http://localhost:9051 | ✅ Running | MCP protocol interface for AI assistants |

## Connecting Claude Desktop

### Step 1: Install Claude Desktop

If you haven't already, download and install [Claude Desktop](https://claude.ai/download) from Anthropic.

### Step 2: Configure MCP Settings

1. Open Claude Desktop
2. Go to Settings → Features → Model Context Protocol
3. Add a new server with these settings:

```json
{
  "archon": {
    "command": "npx",
    "args": [
      "node",
      "-e",
      "const { Client } = require('@modelcontextprotocol/sdk/client'); const { SSEClientTransport } = require('@modelcontextprotocol/sdk/client/sse'); (async () => { const transport = new SSEClientTransport(new URL('http://localhost:9051')); const client = new Client({ name: 'claude-desktop', version: '1.0.0' }, { capabilities: {} }); await client.connect(transport); })();"
    ]
  }
}
```

### Step 3: Restart Claude Desktop

After adding the configuration, restart Claude Desktop to enable the MCP connection.

## Alternative: Using HTTP Client

For a simpler setup, you can also use a basic HTTP client approach:

```json
{
  "archon": {
    "command": "curl",
    "args": [
      "-X", "POST",
      "-H", "Content-Type: application/json",
      "http://localhost:9051/mcp"
    ]
  }
}
```

## Available MCP Tools

Once connected, your AI assistant will have access to these Archon tools:

### Knowledge Management
- **`search_knowledge`**: Search across all documents, websites, and knowledge sources
- **`get_document`**: Retrieve specific documents or content
- **`list_sources`**: View all knowledge sources and their metadata

### Project Management  
- **`list_projects`**: Get all projects and their status
- **`create_project`**: Create new projects with AI assistance
- **`get_project_details`**: Retrieve detailed project information
- **`manage_tasks`**: Create, update, and track project tasks

### Real-time Operations
- **`crawl_website`**: Crawl and index new websites or documentation
- **`upload_document`**: Process and add new documents to the knowledge base
- **`get_status`**: Check the status of ongoing operations

## Testing the Integration

### 1. Basic Connection Test

In Claude Desktop, try asking:
```
"Can you search my knowledge base for information about [topic]?"
```

### 2. Project Management Test

Try:
```
"Show me my current projects and their status"
```

### 3. Knowledge Search Test

Try:
```
"Search for any documentation about [specific technology] in my knowledge base"
```

## Troubleshooting

### Connection Issues

If Claude Desktop can't connect to Archon:

1. **Check Services**: Ensure all Archon services are running:
   ```bash
   cd /Users/krishna/Projects/archon
   docker-compose ps
   ```

2. **Check MCP Server Health**:
   ```bash
   curl http://localhost:9051/health
   ```

3. **View MCP Server Logs**:
   ```bash
   docker-compose logs -f archon-mcp
   ```

### Permission Issues

If you get permission errors:

1. Make sure your Supabase credentials are properly configured in `.env`
2. Check that the API keys are set up in the Archon UI at http://localhost:9737

### Network Issues

If running on a different machine or network:

1. Update the MCP configuration to use your machine's IP address instead of `localhost`
2. Ensure firewall rules allow connections on ports 9051, 9181, and 9737

## Advanced Configuration

### Custom MCP Server URL

If you've changed the default ports or are running remotely, update the URL in your MCP configuration:

```json
{
  "archon": {
    "command": "...",
    "args": ["...", "http://YOUR_IP:YOUR_PORT"]
  }
}
```

### Multiple AI Assistants

You can connect multiple AI tools to the same Archon instance. Each tool will have independent access to your knowledge base and projects.

## Security Considerations

- The MCP server is currently configured for local development
- For production deployments, consider implementing authentication
- Ensure your Supabase credentials are kept secure
- Monitor access logs in the Archon UI

## Getting Help

If you encounter issues:

1. Check the logs: `docker-compose logs`
2. Verify your `.env` configuration
3. Test the web UI at http://localhost:9737
4. Consult the main [README.md](../README.md) for troubleshooting

## Next Steps

Once connected:

1. **Upload Knowledge**: Add documentation, PDFs, or crawl websites
2. **Create Projects**: Organize your work with hierarchical project structure  
3. **Collaborate**: Use AI assistants to help generate content, manage tasks, and search knowledge
4. **Monitor**: Use the web UI to track crawling, processing, and AI operations

Your AI assistants now have access to your entire knowledge base and can help you manage projects more effectively!