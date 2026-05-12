"""



Prerequisites:
    az login

    Set environment variables before running:
        $env:FOUNDRY_PROJECT_ENDPOINT = "https://your-project.services.ai.azure.com"
        $env:FOUNDRY_MODEL = "gpt-4o"

Usage:
    python test_mcp.py
"""

import asyncio
import os
import sys

import requests

from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.foundry import FoundryChatClient
from azure.identity.aio import DefaultAzureCredential

MCP_URL = "https://learn.microsoft.com/api/mcp"
APIM_KEY = ""
FOUNDRY_PROJECT_ENDPOINT = ""
FOUNDRY_MODEL = "gpt-4o"


def check_connectivity():
    """Quick HTTP check to verify the MCP endpoint is reachable through APIM."""
    print("=" * 60)
    print("Step 1: Checking MCP server connectivity...")
    print(f"  URL: {MCP_URL}")
    print("=" * 60)

    try:
        resp = requests.post(
            MCP_URL,
            headers={
                "Ocp-Apim-Subscription-Key": APIM_KEY,
                "Content-Type": "application/json",
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "connectivity-check", "version": "1.0.0"},
                },
            },
            timeout=15,
        )
        print(f"\n  HTTP {resp.status_code}")
        if resp.status_code == 200:
            print("  MCP server is reachable!")
            try:
                print(f"  Server response: {resp.json()}")
            except Exception:
                pass
            return True
        elif resp.status_code == 403:
            print("  BLOCKED (403 Forbidden).")
            print("  Check: Is VPN connected? Is the APIM subscription key correct?")
            return False
        else:
            print(f"  Response: {resp.text[:300]}")
            return True  # Non-403 means we at least reached APIM
    except requests.ConnectionError:
        print("\n  Connection FAILED — cannot reach the server.")
        print("  Make sure VPN is connected and try again.")
        return False
    except Exception as e:
        print(f"\n  Error: {e}")
        return False


async def interactive_chat():
    """Interactive chat loop with the  MCP agent."""

    if not FOUNDRY_PROJECT_ENDPOINT:
        print("\nError: FOUNDRY_PROJECT_ENDPOINT environment variable is required.")
        print("  Set it before running:")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Step 2: Starting interactive agent with  MCP tools...")
    print('  Type "quit" or "exit" to stop.')
    print("=" * 60)

    try:
        async with DefaultAzureCredential() as credential:
            client = FoundryChatClient(
                project_endpoint=FOUNDRY_PROJECT_ENDPOINT,
                model=FOUNDRY_MODEL,
                credential=credential,
            )
            async with Agent(
                client=client,
                name="MCP-Test-Agent",
                instructions=(
                    "You are a helpful assistant with access to MCP tools. "
                    "Use the available tools to answer the user's questions. "
                    "Be concise and helpful."
                ),
                tools=MCPStreamableHTTPTool(
                    name="mcp-tools",
                    url=MCP_URL,
                    header_provider=lambda kwargs: {
                        "Ocp-Apim-Subscription-Key": APIM_KEY
                    },
                ),
            ) as agent:
                # Auto-discover tools on startup
                print("\n  Discovering available MCP tools...\n")
                result = await agent.run(
                    "List all tools available to you with a brief description of each."
                )
                print(f"Agent: {result.text}")

                # Interactive loop
                while True:
                    try:
                        user_input = input("\nYou: ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print("\nGoodbye!")
                        break

                    if not user_input:
                        continue
                    if user_input.lower() in ("quit", "exit"):
                        print("Goodbye!")
                        break

                    try:
                        result = await agent.run(user_input)
                        print(f"\nAgent: {result.text}")
                    except Exception as e:
                        print(f"\n  Error: {e}")

    except Exception as e:
        print(f"\nFailed to start agent: {e}")
        print(
            "  Make sure you have run 'az login' and your Foundry endpoint is correct."
        )
        sys.exit(1)


async def main():
    if not check_connectivity():
        sys.exit(1)
    await interactive_chat()


if __name__ == "__main__":
    asyncio.run(main())
