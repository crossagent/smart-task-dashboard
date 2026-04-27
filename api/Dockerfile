# Use Postgres 17 as the foundation for the Hub
FROM postgres:17-bookworm

# Install Python and core utilities for the simulation
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (standard for all our agents)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set up the application directory
WORKDIR /app

# Copy the specialized hub entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

# Entrypoint orchestration
ENTRYPOINT ["/entrypoint.sh"]

# Default command: Start the Hub MCP Server
CMD ["python3", "-m", "src.server"]
