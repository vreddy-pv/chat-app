# Chat Application for Todo Service

This simple Node.js chat server demonstrates how to interact with the `todo-service` via the MCP server (`todo-service-mcp`).

## Setup

1. Install dependencies:
   ```bash
   cd chat-app
   npm install
   ```

2. Ensure the `todo-service` backend and the Python MCP server are running.
   - Backend by running `mvn spring-boot:run` in the `todo-service` folder.
   - MCP server with `python ../todo-service-mcp/server.py` from this directory or via VS Code debug.

3. Start the chat server:
   ```bash
   npm start
   ```

4. Open `http://localhost:3000` in your browser to access a simple chat UI.
   Type a message and press **Enter**. The client will send the text to `/chat` and display the response.

   (You can still call `/chat` directly with JSON as before.)

## How it works

- The server uses `@modelcontextprotocol/mcp-sdk` to create an MCP client that communicates over stdio with `todo-service-mcp`.
- When a message arrives, the client asks the MCP server for context and optionally retrieves data from the REST API of `todo-service`.
- This is a starting point; you can extend the message handler to implement natural-language understanding or AI features.
