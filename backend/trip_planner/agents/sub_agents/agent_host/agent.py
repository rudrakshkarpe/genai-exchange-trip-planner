import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, AsyncIterable, List
import requests

import httpx
import nest_asyncio
from a2a.client import A2ACardResolver
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendMessageResponse,
    SendMessageSuccessResponse,
    Task,
)
from dotenv import load_dotenv
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from google.adk import Agent
from google.adk.tools import FunctionTool

from agent_host.remote_agent_connection import RemoteAgentConnections
from agent_host import prompt
from agent_host.tools import _load_precreated_itinerary

load_dotenv("../../.env")
nest_asyncio.apply()

class HostAgent:
    """The Host agent."""

    def __init__(self):
        self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
        self.cards: dict[str, AgentCard] = {}
        self.agents: str = ""
        self._user_id = "host_agent"


        self._agent = self.create_agent()
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    async def _async_init_components(self, remote_agent_addresses: List[str]):
        async with httpx.AsyncClient(timeout=30) as client:
            for address in remote_agent_addresses:
                card_resolver = A2ACardResolver(client, address)
                try:
                    card = await card_resolver.get_agent_card()
                    remote_connection = RemoteAgentConnections(
                        agent_card=card, agent_url=address
                    )
                    self.remote_agent_connections[card.name] = remote_connection
                    self.cards[card.name] = card
                    print(f"\n=== Agent Card for {card.name} ===")
                    print(json.dumps(card.model_dump(), indent=2))
                except httpx.ConnectError as e:
                    print(f"ERROR: Failed to get agent card from {address}: {e}")
                except Exception as e:
                    print(f"ERROR: Failed to initialize connection for {address}: {e}")

        agent_info = [
            json.dumps({"name": card.name, "description": card.description})
            for card in self.cards.values()
        ]
        print("agent_info:", agent_info)
        self.agents = "\n".join(agent_info) if agent_info else "No relevant tools found"

    @classmethod
    async def create(
        cls,
        remote_agent_addresses: List[str],
    ):
        instance = cls()
        await instance._async_init_components(remote_agent_addresses)
        return instance
    

    def create_agent(self) -> Agent:

        return Agent(
            model="gemini-2.5-flash",
            name="Host_Agent",
            instruction=self.root_instruction,
            description="You are a travel AI agent, that helps the user plan their trip by coordinating with other specialized agents. You have access to tools that allow you to communicate with other agents, such as the Inspiration agent, Planning agent, Booking agent, Pre-Trip agent, In-Trip agent and Post-Trip agent. Your goal is to understand the user's travel needs and delegate tasks to the appropriate agents to provide a comprehensive travel planning experience.",
            tools=[
                self.send_message,
            ],
            before_agent_callback=_load_precreated_itinerary,
        )


    def root_instruction(self, context: ReadonlyContext) -> str:
        return prompt.ROOT_AGENT_INSTR

    async def stream(
        self, query: str, session_id: str
    ) -> AsyncIterable[dict[str, Any]]:
        """
        Streams the agent's response to a given query.
        """
        session = await self._runner.session_service.get_session(
            app_name=self._agent.name,
            user_id=self._user_id,
            session_id=session_id,
        )
        content = types.Content(role="user", parts=[types.Part.from_text(text=query)])
        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                state={},
                session_id=session_id,
            )
        async for event in self._runner.run_async(
            user_id=self._user_id, session_id=session.id, new_message=content
        ):
            if event.is_final_response():
                response = ""
                if (
                    event.content
                    and event.content.parts
                    and event.content.parts[0].text
                ):
                    response = "\n".join(
                        [p.text for p in event.content.parts if p.text]
                    )
                yield {
                    "is_task_complete": True,
                    "content": response,
                }
            else:
                yield {
                    "is_task_complete": False,
                    "updates": "The host agent is thinking...",
                }

    async def send_message(self, agent_name: str, task: str, tool_context: ToolContext):
        """Sends a task to a remote agent: Inspiration agent, Planning agent, booking agent, Pre-Trip agent, In-Trip agent or Post-Trip agent."""
        print("Available agents:---------------------", self.remote_agent_connections.keys())
        formatted = " ".join(word.capitalize() for word in agent_name.split("_"))
        formatted_agent_name = f"{formatted} (A2A)"
        print("send_message called with agent_name:---------------------", formatted_agent_name)
        if formatted_agent_name not in self.remote_agent_connections:
            raise ValueError(f"Agent {formatted_agent_name} not found")
        client = self.remote_agent_connections[formatted_agent_name]

        if not client:
            raise ValueError(f"Client not available for {formatted_agent_name}")

        # Simplified task and context ID management
        state = tool_context.state
        task_id = state.get("task_id", str(uuid.uuid4()))
        context_id = state.get("context_id", str(uuid.uuid4()))
        message_id = str(uuid.uuid4())

        payload = {
            "message": {
                "role": "user",
                "parts": [
                    {"type": "text", "text": task}
                ],
                "messageId": message_id,
            },
            "taskId": task_id,
            "contextId": context_id,
        }

        print("payload sending:-----------------", payload)

        message_request = SendMessageRequest(
            id=message_id, params=MessageSendParams.model_validate(payload)
        )
        send_response: SendMessageResponse = await client.send_message(message_request)
        print("send_response", send_response)

        if not isinstance(
            send_response.root, SendMessageSuccessResponse
        ) or not isinstance(send_response.root.result, Task):
            print("Received a non-success or non-task response. Cannot proceed.")
            return

        response_content = send_response.root.model_dump_json(exclude_none=True)
        json_content = json.loads(response_content)

        resp = []
        if json_content.get("result", {}).get("artifacts"):
            for artifact in json_content["result"]["artifacts"]:
                if artifact.get("parts"):
                    resp.extend(artifact["parts"])
        return resp


def _get_initialized_host_agent_sync():
    """Synchronously creates and initializes the HostAgent."""

    async def _async_main():
        # Hardcoded URLs for the friend agents
        agent_urls = [
            "http://localhost:8001",  # Inspiration Agent
            "http://localhost:8002",  # Planning Agent
            "http://localhost:8003",  # Booking Agent
            "http://localhost:8004",  # Pre-Trip Agent
            "http://localhost:8005",  # In-Trip Agent
            "http://localhost:8006",  # Post-Trip Agent
        ]

        print("initializing host agent")
        hosting_agent_instance = await HostAgent.create(
            remote_agent_addresses=agent_urls
        )
        print("HostAgent initialized")
        return hosting_agent_instance.create_agent()
    
    try:
        return asyncio.run(_async_main())
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            print(
                f"Warning: Could not initialize HostAgent with asyncio.run(): {e}. "
                "This can happen if an event loop is already running (e.g., in Jupyter). "
                "Consider initializing HostAgent within an async function in your application."
            )
            # nest_asyncio.apply()
            # return asyncio.get_event_loop().run_until_complete(_async_main())
        else:
            raise


print("Initializing Host Agent...")
root_agent = _get_initialized_host_agent_sync()