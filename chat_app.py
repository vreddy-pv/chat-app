import asyncio
import os
from contextlib import asynccontextmanager, AsyncExitStack
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# MCP and AI Imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from cohere import AsyncClient as AsyncCohereClient

load_dotenv()

# --- Configuration ---
# Ensure this path is correct for your environment
TODO_SERVICE_MCP_PATH = "C:/Veera/AI/claude-code/unified-mcp-server"
MAX_HOPS = 3  # Safety break

class AppState:
    mcp_session: ClientSession = None
    cohere_client: AsyncCohereClient = None
    exit_stack: AsyncExitStack = None

app_state = AppState()

# --- FastAPI Lifespan Management ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Startup: Initializing AI & MCP Orchestrator...")
    app_state.exit_stack = AsyncExitStack()
    
    try:
        # 1. Initialize Cohere Client
        app_state.cohere_client = AsyncCohereClient(os.getenv("COHERE_API_KEY"))
        
        # 2. Setup MCP Parameters (Using .venv python for isolated dependencies)
        server_params = StdioServerParameters(
            command=f"{TODO_SERVICE_MCP_PATH}/.venv/Scripts/python.exe",
            args=[f"{TODO_SERVICE_MCP_PATH}/server.py"]
        )

        # 3. Establish Persistent Connection using ExitStack
        reader, writer = await app_state.exit_stack.enter_async_context(stdio_client(server_params))
        session = await app_state.exit_stack.enter_async_context(ClientSession(reader, writer))
        
        await session.initialize()
        app_state.mcp_session = session
        print("✅ MCP Tool Server session initialized and ready.")

        yield  # The application runs here

    finally:
        print("🛑 Shutdown: Closing services...")
        await app_state.exit_stack.aclose()
        print("Services closed.")

app = FastAPI(lifespan=lifespan)

# --- API Models ---
class ChatMessage(BaseModel):
    message: str

# --- Core Logic: Mapping MCP to Cohere ---

def map_mcp_to_cohere_tools(mcp_tools):
    """Maps MCP JSON Schema to Cohere's parameter_definitions format."""
    cohere_tools = []
    for tool in mcp_tools:
        # Cohere V1 format uses parameter_definitions
        cohere_tools.append({
            "name": tool.name,
            "description": tool.description,
            "parameter_definitions": tool.inputSchema.get("properties", {})
        })
    return cohere_tools

# --- API Routes ---

@app.get("/", response_class=HTMLResponse)
async def get_root():
    # This is a Python function, but it returns a string of HTML and JavaScript
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Unified AI Manager</title>
        <style>
            body{font-family:sans-serif; max-width:800px; margin:auto; padding:20px}
            #chatbox{height:500px; border:1px solid #ddd; overflow-y:auto; padding:15px; background:#f9f9f9; border-radius:8px; margin-bottom:10px}
            .msg{margin-bottom:10px}
            input{width:100%; padding:12px; border-radius:4px; border:1px solid #ccc}
        </style>
    </head>
    <body>
        <h1>Financial AI Assistant</h1>
        <div id="chatbox"></div>
        <input type="text" id="usermsg" placeholder="Ask about accounts or todos..." onkeypress="handleKey(event)" />

        <script>
            // --- THIS IS JAVASCRIPT CODE INSIDE A PYTHON STRING ---
            
            // CORRECT: Use 'function', NOT 'def'
            async function handleKey(e) {
                if (e.key === 'Enter') {
                    const input = e.target;
                    const msg = input.value.trim();
                    if (!msg) return;
                    
                    input.value = '';
                    append('You', msg);

                    try {
                        const response = await fetch('/chat', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({message: msg})
                        });
                        const data = await response.json();
                        append('Assistant', data.reply);
                    } catch (err) {
                        append('System', 'Error: Could not reach the AI server.');
                    }
                }
            }

            function append(role, text) {
                const chatbox = document.getElementById('chatbox');
                const div = document.createElement('div');
                div.className = 'msg';
                // Formatting new lines for the browser
                div.innerHTML = `<b>${role}:</b> ${text.replace(/\\n/g, '<br>')}`;
                chatbox.appendChild(div);
                chatbox.scrollTop = chatbox.scrollHeight;
            }
        </script>
    </body>
    </html>
    """

@app.post("/chat")
async def chat_endpoint(chat_message: ChatMessage):
    if not app_state.mcp_session:
        return JSONResponse(status_code=503, content={"reply": "MCP Service not ready."})

    try:
        # 1. Prepare Tools and History
        mcp_result = await app_state.mcp_session.list_tools()
        tools = map_mcp_to_cohere_tools(mcp_result.tools)

        chat_history = []
        current_message = chat_message.message
        hops = 0

        # 2. Initial Model Call
        response = await app_state.cohere_client.chat(
            message=current_message,
            tools=tools,
            chat_history=chat_history,
            model="command-r-plus-08-2024"
        )

        # 3. Unified Tool Loop with MAX_HOPS safety
        while response.tool_calls and hops < MAX_HOPS:
            hops += 1
            print(f"DEBUG: Hop {hops} - Model requested {len(response.tool_calls)} tool(s)")
            
            # Save the model's intent to history
            chat_history.append({
                "role": "CHATBOT", 
                "message": response.text or "", 
                "tool_calls": response.tool_calls
            })
            
            tool_results = []
            for tool_call in response.tool_calls:
                print(f"🛠️ Executing Tool: {tool_call.name}")
                
                # Execute tool via MCP
                mcp_call_result = await app_state.mcp_session.call_tool(
                    name=tool_call.name,
                    arguments=tool_call.parameters
                )
                
                # Correct indexing
                result_text = mcp_call_result.content[0].text if mcp_call_result.content else "Success"
                
                tool_results.append({
                    "call": tool_call,
                    "outputs": [{"text": result_text}]
                })

            # 4. Return results to Model (Note: message="" is vital here)
            response = await app_state.cohere_client.chat(
                message="", 
                tools=tools,
                tool_results=tool_results,
                chat_history=chat_history,
                model="command-r-plus-08-2024"
            )

        if hops >= MAX_HOPS:
            print("⚠️ Warning: MAX_HOPS reached. Stopping loop.")

        return {"reply": response.text}

    except Exception as e:
        print(f"❌ Error: {e}")
        return JSONResponse(status_code=500, content={"reply": f"Internal Error: {str(e)}"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)