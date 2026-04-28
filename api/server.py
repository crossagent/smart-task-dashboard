import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Simple flat imports
from .dashboard_api import router as dashboard_router

logger = logging.getLogger("smart_task.dashboard_server")
logging.basicConfig(level=logging.INFO)

# Create the main FastAPI app
app = FastAPI(
    title="Smart Task Hub Dashboard"
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
    # Check which path exists
    dist_path = "frontend/dist" if os.path.exists("frontend/dist") else "dashboard-server/frontend/dist"
    index_file = os.path.join(dist_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Smart Task Dashboard API is running"}

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "45666"))
    logger.info(f"Dashboard running on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
