# main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
from routers import ollama as ollama_router
from routers import projects as projects_router
from config import API_HOST, API_PORT, RECONNECT_PROJECTS, RESUME_PROJECTS
from services import docker_service
# Import from the new state module
from core.state_manager import active_projects_state, add_project_to_state, remove_project_from_state

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lifespan Manager (Updated Imports)
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("MRM36 Service starting up...")
    if docker_service.docker_client is None:
        logger.error("Docker client initialization failed. Service may be degraded.")
    else:
        if RECONNECT_PROJECTS:
            logger.info("Reconnecting to existing projects...")
            try:
                existing_containers = await docker_service.list_mrm36_containers()
                for container_info in existing_containers:
                    p_id = container_info["project_id"]
                    c_id = container_info["container_id"]
                    c_status = container_info["status"]
                    logger.info(f"Found existing project '{p_id}' (Container: {c_id}, Status: {c_status})")

                    initial_orchestration_status = 'idle'
                    if c_status == 'running':
                        if RESUME_PROJECTS:
                            logger.info(f"Marking project '{p_id}' for auto-resume.")
                            initial_orchestration_status = 'running'
                        else:
                            logger.info(f"Project '{p_id}' reconnected but set to idle (RESUME_PROJECTS=False).")
                            initial_orchestration_status = 'idle'

                    # Use the imported function to update state
                    add_project_to_state(
                        project_id=p_id,
                        initial_status=initial_orchestration_status,
                        container_id=c_id,
                        container_status=c_status
                    )
                logger.info(f"Finished reconnecting. Active projects state: {active_projects_state}") # Log the imported state dict

            except Exception as e:
                 logger.error(f"Error during project reconnection: {e}", exc_info=True)
        else:
            logger.info("Skipping project reconnection (RECONNECT_PROJECTS=False).")

    yield # Service runs here

    logger.info("MRM36 Service shutting down...")
    # Clear the imported state dictionary on shutdown
    active_projects_state.clear()

# --- FastAPI App Definition ---
app = FastAPI(
    title="MRM36 Agent Service",
    version="0.2.0",
    description="Service to manage agentic tasks within containerized project environments.",
    lifespan=lifespan
)

# Include the API routers
app.include_router(ollama_router.router)
app.include_router(projects_router.router)

@app.get("/", tags=["Root"])
async def root():
    return {"message": "Welcome to the MRM36 Agent Service API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=API_HOST, port=API_PORT, log_level="info", reload=True) # Use string "main:app" for reload