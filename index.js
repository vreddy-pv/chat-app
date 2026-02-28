const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios');
const { createMCPClient } = require('@modelcontextprotocol/mcp-sdk');

// configure MCP client pointing at the todo-service-mcp server
const mcpClient = createMCPClient({
  type: 'stdio',
  command: 'python',
  args: ['../todo-service-mcp/server.py']
});

// simple express app for chat
const app = express();
app.use(bodyParser.json());
// serve static files for web UI
app.use(express.static('public'));

app.post('/chat', async (req, res) => {
  const { message } = req.body;
  try {
    // request context from MCP server (for now the stub just returns {})
    const context = await mcpClient.requestContext({ prompt: message });

    // optionally use todo-service REST endpoints
    // example: if user asks for accounts, fetch from backend
    let todoData = null;
    if (/accounts?/i.test(message)) {
      const resp = await axios.get('http://localhost:8081/accounts');
      todoData = resp.data;
    }

    res.json({ reply: `You said: ${message}`, context, todoData });
  } catch (err) {
    console.error('chat error', err);
    res.status(500).json({ error: err.message });
  }
});

app.listen(3000, () => console.log('Chat server listening on http://localhost:3000'));