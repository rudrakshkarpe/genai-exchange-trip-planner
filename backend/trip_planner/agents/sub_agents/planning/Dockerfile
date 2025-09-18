FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

EXPOSE 8080
WORKDIR /app

# Copy the entire backend directory to maintain proper package structure
COPY ../../../.. ./

# Set the working directory to the planning agent
WORKDIR /app/genai-exchange-trip-planner/backend/trip_planner/agents/sub_agents/planning

# Set PYTHONPATH to include the backend directory for proper imports
ENV PYTHONPATH="/app/genai-exchange-trip-planner/backend:$PYTHONPATH"

RUN uv sync

ENTRYPOINT ["uv", "run", ".", "--host", "0.0.0.0", "--port", "8002"]
