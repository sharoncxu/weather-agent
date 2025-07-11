"""Flask app with integrated MCP weather assistant
# Run this flask app
> pip install flask flask-cors mcp openai
> python app.py
"""
import asyncio
import json
import os
from typing import Dict, Optional
from contextlib import AsyncExitStack
import threading
import concurrent.futures

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

from openai import OpenAI
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self._servers = {}
        self._tool_to_server_map = {}
        self.exit_stack = AsyncExitStack()
        # To authenticate with the model you will need to generate a personal access token (PAT) in your GitHub settings.
        # Create your PAT token by following instructions here: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens
        self.openai = OpenAI(
            base_url = "https://models.inference.ai.azure.com",
            api_key = os.environ["GITHUB_TOKEN"],
            default_query = {
                "api-version": "2024-08-01-preview",
            },
        )

    async def connect_stdio_server(self, server_id: str, command: str, args: list[str], env: Dict[str, str]):
        """Connect to an MCP server using STDIO transport
        
        Args:
            server_id: Unique identifier for this server connection
            command: Command to run the MCP server
            args: Arguments for the command
            env: Optional environment variables
        """
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env
        )
        
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))
        await session.initialize()
        
        # Register the server
        await self._register_server(server_id, session)
    
    async def connect_sse_server(self, server_id: str, url: str, headers: Dict[str, str]):
        """Connect to an MCP server using SSE transport
        
        Args:
            server_id: Unique identifier for this server connection
            url: URL of the SSE server
            headers: Optional HTTP headers
        """
        sse_context = await self.exit_stack.enter_async_context(sse_client(url=url, headers=headers))
        read, write = sse_context
        session = await self.exit_stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        
        # Register the server
        await self._register_server(server_id, session)
    
    async def _register_server(self, server_id: str, session: ClientSession):
        """Register a server and its tools in the client
        
        Args:
            server_id: Unique identifier for this server
            session: Connected ClientSession
        """
        # List available tools
        response = await session.list_tools()
        tools = response.tools
        
        # Store server connection info
        self._servers[server_id] = {
            "session": session,
            "tools": tools
        }
        
        # Update tool-to-server mapping
        for tool in tools:
            self._tool_to_server_map[tool.name] = server_id
            
        print(f"\nConnected to server '{server_id}' with tools:", [tool.name for tool in tools])

    async def chatWithTools(self, messages: list[any]) -> str:
        """Chat with model and using tools
        Args:
            messages: Messages to send to the model
        """
        if not self._servers:
            raise ValueError("No MCP servers connected. Connect to at least one server first.")

        # Collect tools from all connected servers
        available_tools = []
        for server_id, server_info in self._servers.items():
            for tool in server_info["tools"]:
                available_tools.append({ 
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema
                    },
                })

        while True:

            # Call model
            response = self.openai.chat.completions.create(
                messages = messages,
                model = "gpt-4o",
                tools=available_tools,
                response_format = {
                    "type": "text"
                },
                temperature = 1,
                top_p = 1,
            )
            hasToolCall = False

            if response.choices[0].message.tool_calls:
                for tool in response.choices[0].message.tool_calls:
                    hasToolCall = True
                    tool_name = tool.function.name
                    
                    # Parse tool arguments, ensuring we always have a valid object
                    try:
                        tool_args = json.loads(tool.function.arguments) if tool.function.arguments else {}
                        if tool_args is None:
                            tool_args = {}
                        if not isinstance(tool_args, dict):
                            tool_args = {}
                    except (json.JSONDecodeError, TypeError):
                        tool_args = {}
                    
                    messages.append({
                        "role": "assistant", 
                        "tool_calls": [{
                            "id": tool.id,
                            "type": "function",
                            "function": {
                                "name": tool.function.name,
                                "arguments": tool.function.arguments,
                            }
                        }]
                    })
                
                    # Find the appropriate server for this tool
                    if tool_name in self._tool_to_server_map:
                        server_id = self._tool_to_server_map[tool_name]
                        server_session = self._servers[server_id]["session"]
                        
                        # Execute tool call on the appropriate server
                        result = await server_session.call_tool(tool_name, arguments=tool_args)
                        print(f"[Server '{server_id}' call tool '{tool_name}' with args {tool_args}]: {result.content}")

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool.id,
                            "content": result.content,
                        })
            else:
                model_response = response.choices[0].message.content
                messages.append({
                    "role": "assistant",
                    "content": model_response
                })
                print(f"[Model Response]: {model_response}")
        
            if not hasToolCall:
                break
        
        return model_response
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()
        await asyncio.sleep(1)

# Global variables to store the latest model response and message history
latest_model_response = "No weather data available yet. Please request weather information first."
message_history = []  # Store conversation history
mcp_client = None

async def send_user_message(user_message: str):
    """Send a user message and get AI response"""
    global latest_model_response, mcp_client, message_history
    
    try:
        mcp_client = MCPClient()
        
        # Initialize with system message if history is empty
        if not message_history:
            message_history.append({
                "role": "system",
                "content": "You are in charge of helping the user get ready to leave the house. Use the get-weather tool to check the current weather for the current city. Check the air quality index to see if its suitable to go outside today. Then make recommendations on what the user should do before going outside. Remove the emojis. Display the result in plain text instead of Markdown.",
            })
        
        # Add the new user message to history
        user_message_obj = {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": user_message,
                },
            ],
        }
        message_history.append(user_message_obj)
        
        await mcp_client.connect_stdio_server(
            "weather", 
            "npx", 
            [
                "-y",
                "@timlukahorstmann/mcp-weather",
            ],
            {
                "ACCUWEATHER_API_KEY": os.environ.get("ACCUWEATHER_API_KEY", ""),
            }
        )
        
        # Pass the entire message history to maintain context
        latest_model_response = await mcp_client.chatWithTools(message_history.copy())
        
        # Add the assistant's response to history
        message_history.append({
            "role": "assistant",
            "content": latest_model_response
        })
        
        return latest_model_response
        
    except Exception as e:
        latest_model_response = f"Error processing message: {str(e)}"
        # Add error to history as well
        message_history.append({
            "role": "assistant", 
            "content": latest_model_response
        })
        return latest_model_response
    finally:
        if mcp_client:
            await mcp_client.cleanup()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/api/send_message', methods=['POST'])
def send_message():
    """API endpoint to send a user message"""
    data = request.get_json()
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({"error": "Message is required"}), 400
    
    # Run the async function in a thread
    def async_send_message():
        return asyncio.run(send_user_message(user_message))
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(async_send_message)
        result = future.result()
    
    return jsonify({"response": result, "message": user_message})

@app.route('/api/weather')
def get_weather():
    """API endpoint to get weather information (legacy endpoint)"""
    city = request.args.get('city', 'Seattle')  # Default to Seattle if no city provided
    
    # Create a weather-specific message
    weather_message = f"I'm in {city}. What do I need to do before leaving the house?"
    
    # Run the async function in a thread
    def async_weather():
        return asyncio.run(send_user_message(weather_message))
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(async_weather)
        result = future.result()
    
    return jsonify({"weatherInfo": result, "city": city})

@app.route('/api/model_response')
def get_model_response():
    """API endpoint to get the latest model response"""
    global latest_model_response
    return jsonify({"modelResponse": latest_model_response})

@app.route('/api/message_history')
def get_message_history():
    """API endpoint to get the complete message history"""
    global message_history
    return jsonify({"messageHistory": message_history})

@app.route('/api/clear_history', methods=['POST'])
def clear_message_history():
    """API endpoint to clear the message history"""
    global message_history, latest_model_response
    message_history = []
    latest_model_response = "Message history cleared. Please request weather information."
    return jsonify({"status": "success", "message": "Message history cleared"})

@app.route('/')
def index():
    """Serve the main HTML page"""
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True, port=5000)