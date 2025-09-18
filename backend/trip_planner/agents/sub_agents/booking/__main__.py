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
from trip_planner.agents.sub_agents.booking.agent import create_agent
from trip_planner.agents.sub_agents.booking.agent_executor import BookingExecutor
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
    port = 8003

    # agent metadata
    capabilities = AgentCapabilities(streaming=True)
    skill = AgentSkill(
        id="booking_information",
        name="Booking Information",
        description="Given an itinerary, the agent completes the bookings of the items by handling payment choices and processing. The agent has access to tools to confirm reservation, show user's payment choices, and process payment.",
        tags=["booking", "payment", "transaction", "reservation", "payment choice"],
        examples=["Can you book the flights and hotels?", "Can you book the flight using Credit Card?"],
    )
    agent_card = AgentCard(
        name="Booking Agent (A2A)",
        description="Complete booking of the items based on the provided itinerary.",
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
    agent_executor = BookingExecutor(runner)

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
    try:
        main()
    except Exception as e:
        import traceback, time
        traceback.print_exc()
        time.sleep(5)  # keep window open for 10s if crash