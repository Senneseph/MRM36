from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
from routers import ollama as ollama_router
from routers import projects as projects_router
from config import API_HOST, API_PORT
# Import docker_service just to ensure client initialization logging happens early
from services import docker_service # noqa F401 (unused import ok here)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lifespan can manage shared resources like DB connections or HTTP clients if needed
# For now, Ollama client is per-request, Docker client is global in docker_service
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("MRM36 Service starting up...")
    # Initialize other resources here if needed
    yield
    logger.info("MRM36 Service shutting down...")

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
    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="info")