import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

# Simple flat imports
from .supervisor import agent_supervisor
from .dashboard_api import router as dashboard_router

logger = logging.getLogger("smart_task.dashboard_server")
logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """Lifecycle hook to start background processes."""
    logger.info("Starting up Dashboard Server background tasks...")

    if os.getenv("DOCKER_MANAGED_AGENTS", "false").lower() != "true":
        agent_supervisor.bootstrap()
    else:
        logger.info("Agents are managed by Docker. Loading config...")
        agent_supervisor.load_config()
    
    yield
    logger.info("Shutting down Dashboard Server...")

# Create the main FastAPI app
app = FastAPI(
    title="Smart Task Hub Dashboard", 
    lifespan=app_lifespan
)

# Add CORS to the main app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard_router)

# Mount frontend if it exists
if os.path.exists("frontend/dist"):
    app.mount("/dashboard", StaticFiles(directory="frontend/dist", html=True), name="dashboard")
elif os.path.exists("dashboard-server/frontend/dist"):
    app.mount("/dashboard", StaticFiles(directory="dashboard-server/frontend/dist", html=True), name="dashboard")

@app.get("/")
async def root():
    return {"message": "Smart Task Dashboard API is running"}

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "45666"))
    logger.info(f"Dashboard running on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
