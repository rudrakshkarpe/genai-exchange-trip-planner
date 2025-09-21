FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install build dependencies for packages with native extensions
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 8000
WORKDIR /app

# Copy the entire repository to maintain proper package structure
COPY . ./

# Set the working directory to the planning agent
WORKDIR /app

# Set PYTHONPATH to include the backend directory for proper imports
ENV PYTHONPATH="/app/backend"

RUN uv sync --verbose

ENTRYPOINT ["uv", "run", ".", "--host", "0.0.0.0", "--port", "8000"]
