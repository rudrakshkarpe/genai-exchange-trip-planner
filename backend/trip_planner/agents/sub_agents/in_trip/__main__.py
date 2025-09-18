import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

import logging
import asyncio
import uvicorn
from uvicorn.config import Config
from uvicorn.server import Server
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from trip_planner.agents.sub_agents.in_trip.agent import create_agent
from trip_planner.agents.sub_agents.in_trip.agent_executor import InTripExecutor
from dotenv import load_dotenv
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
load_dotenv("../../.env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    asyncio.run(async_main())

async def async_main():
    """Starts the agent server."""
    host = "localhost"
    port = 8005

    # agent metadata
    capabilities = AgentCapabilities(streaming=True)
    skill = AgentSkill(
        id="in_trip_information",
        name="In Trip Information",
        description="You are a travel concierge. You provide helpful information during the users' trip. The agent has access to sub-agents and tools to handle travel logistics of the trip, monitor aspects of itinerary and bring attention to items that necessitate changes.",
        tags=["in-trip", "daily checks", "travel logistics", "itinerary monitoring", "itinerary changes"],
        examples=[""],
    )
    agent_card = AgentCard(
        name="In Trip Agent (A2A)",
        description="Provide information about what the users need as part of the tour, while they are in the trip.",
        url=f"http://{host}:{port}/",
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=capabilities,
        skills=[skill],
    )

    adk_agent = create_agent()
    
    runner = Runner(
        app_name=agent_card.name,
        agent=adk_agent,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )
    agent_executor = InTripExecutor(runner)

    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=InMemoryTaskStore(),
    )
    app = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )

    config = Config(app.build(), host=host, port=port)
    server = Server(config)
    await server.serve()

if __name__ == "__main__":
    main()