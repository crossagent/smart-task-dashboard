import os
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastmcp.utilities.lifespan import combine_lifespans
from contextlib import asynccontextmanager

# Simple flat imports
from .mcp_app import mcp
from . import tools 
from .supervisor import agent_supervisor
from .dashboard_api import router as dashboard_router
import logging

logger = logging.getLogger("smart_task.mcp_server")
logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """Lifecycle hook to start project-specific background processes."""
    logger.info("Starting up project background tasks...")

    if os.getenv("DOCKER_MANAGED_AGENTS", "false").lower() != "true":
        agent_supervisor.bootstrap()
    else:
        logger.info("Agents are managed by Docker. Loading config...")
        agent_supervisor.load_config()
    
    yield
    logger.info("Shutting down project background tasks...")

# Create the MCP app with streamable-http transport
mcp_app = mcp.http_app(transport="streamable-http")

# Create the main FastAPI app and combine lifespans
app = FastAPI(
    title="Smart Task Hub Dashboard", 
    lifespan=combine_lifespans(app_lifespan, mcp_app.lifespan)
)

# Add CORS to the main app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["mcp-session-id"],
)

app.include_router(dashboard_router)

if os.path.exists("dashboard/dist"):
    app.mount("/dashboard", StaticFiles(directory="dashboard/dist", html=True), name="dashboard")

# Merge MCP routes directly into the main app to avoid mounting/priority issues
for route in mcp_app.routes:
    app.routes.append(route)

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "45666"))
    uvicorn.run(app, host="0.0.0.0", port=port)
