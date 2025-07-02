"""Connect model with mcp tools in Python
# Run this python script
> pip install mcp openai
> python <this-script-path>.py
"""
import asyncio
import json
import os
from typing import Dict, Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

from openai import OpenAI

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

        # Handle tool calls if any
        if response.choices[0].message.tool_calls:
            # Add the assistant's message with tool calls
            messages.append({
                "role": "assistant", 
                "tool_calls": response.choices[0].message.tool_calls
            })
            
            for tool in response.choices[0].message.tool_calls:
                tool_name = tool.function.name
                tool_args = json.loads(tool.function.arguments)
            
                # Find the appropriate server for this tool
                if tool_name in self._tool_to_server_map:
                    server_id = self._tool_to_server_map[tool_name]
                    server_session = self._servers[server_id]["session"]
                    
                    # Execute tool call on the appropriate server
                    result = await server_session.call_tool(tool_name, tool_args)
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool.id,
                        "content": str(result.content),
                    })
            
            # Get final response after tool execution
            final_response = self.openai.chat.completions.create(
                messages = messages,
                model = "gpt-4o",
                response_format = {
                    "type": "text"
                },
                temperature = 1,
                top_p = 1,
            )
            
            final_content = final_response.choices[0].message.content
            messages.append({
                "role": "assistant",
                "content": final_content
            })
            print(final_content)
        else:
            # No tool calls, just add the response
            content = response.choices[0].message.content
            messages.append({
                "role": "assistant",
                "content": content
            })
            print(content)
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()
        await asyncio.sleep(1)

async def main():
    client = MCPClient()
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant with access to weather tools. You can help users check weather conditions, air quality, and provide recommendations. Remove emojis and display results in plain text instead of Markdown.",
        }
    ]
    
    try:
        # Connect to the weather MCP server
        await client.connect_stdio_server(
            "weather-mcp", 
            "node", 
            [
                "C:\\Users\\sharonxu\\mcp-weather-server\\dist\\index.js",
            ],
            {}
        )
        
        print("🌤️ Weather Chat Assistant")
        print("=" * 40)
        print("Type 'quit', 'exit', or 'bye' to end the conversation.")
        print("=" * 40)
        
        # Start the chat loop
        while True:
            # Get user input
            user_input = input("\nYou: ").strip()
            
            # Check for exit commands
            if user_input.lower() in ['quit', 'exit', 'bye', 'q']:
                print("Assistant: Goodbye! Stay safe out there! 👋")
                break
            
            # Skip empty inputs
            if not user_input:
                continue
            
            # Add user message to conversation
            messages.append({
                "role": "user",
                "content": user_input
            })
            
            # Get assistant response with tools
            print("Assistant: ", end="", flush=True)
            await client.chatWithTools(messages)
            
    except KeyboardInterrupt:
        print("\n\nChat interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\nError: {str(e)}")
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())