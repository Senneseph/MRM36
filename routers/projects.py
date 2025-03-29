from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
import logging
from services import docker_service # Import our docker functions

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["Projects"])

# --- Pydantic Models for Requests/Responses (Example) ---
class ProjectCreate(BaseModel):
    project_id: str = Field(..., description="Unique identifier for the project (e.g., 'my-web-app')")
    base_image: str = Field(..., description="Docker image to use for the project environment (e.g., 'mrm36/base-tools:latest')")
    # Add goal, initial plan, etc. later

class ProjectStatus(BaseModel):
    project_id: str
    status: str # e.g., "running", "stopped", "not_found"
    container_id: str | None = None
    workspace_volume: str | None = None

class CommandRequest(BaseModel):
    command: str = Field(..., description="The command to execute inside the project container")

class CommandResponse(BaseModel):
    exit_code: int
    output: str

# --- Project API Endpoints (Stubs & Basic Integration) ---

@router.post("/", summary="Initialize or Start a Project Environment")
async def create_or_start_project(project_data: ProjectCreate) -> ProjectStatus:
    """
    Creates the necessary resources (like Docker volume) and
    starts the containerized environment for a new or existing project.
    If the container exists but is stopped, it starts it.
    """
    try:
        # TODO: Create initial .plan file in the host-side volume mount point or copy it in later
        result = await docker_service.launch_project_container(
            project_id=project_data.project_id,
            image_name=project_data.base_image
        )
        return ProjectStatus(
            project_id=project_data.project_id,
            status=result["status"],
            container_id=result.get("container_id"),
            workspace_volume=result.get("workspace_volume")
        )
    except ConnectionError as e:
         raise HTTPException(status_code=503, detail=f"Docker connection error: {e}")
    except Exception as e:
        logger.error(f"Failed to create/start project {project_data.project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/execute", summary="Execute a command in a Project Container")
async def execute_project_command(project_id: str, request: CommandRequest) -> CommandResponse:
    """
    Sends a command (presumably human-approved) to be executed
    inside the specified project's running container.
    """
    try:
        result = await docker_service.execute_command_in_container(
            project_id=project_id,
            command=request.command
        )
        return CommandResponse(**result)
    except ValueError as e: # Specific error for container not found/running
         raise HTTPException(status_code=404, detail=str(e))
    except ConnectionError as e:
         raise HTTPException(status_code=503, detail=f"Docker connection error: {e}")
    except Exception as e:
        logger.error(f"Failed to execute command in project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/status", summary="Get Project Environment Status")
async def get_project_status(project_id: str):
    """Check if the container for the project exists and its status."""
    logger.warning(f"get_project_status for {project_id} not fully implemented.")
    # TODO: Implement using docker_client.containers.get() and handle NotFound
    raise HTTPException(status_code=501, detail="Not Implemented Yet")


@router.delete("/{project_id}", summary="Stop and Remove a Project Environment")
async def delete_project(project_id: str):
    """Stops and removes the container. Optionally removes the volume."""
    logger.warning(f"delete_project for {project_id} not fully implemented.")
    # TODO: Implement using container.stop(), container.remove(), volume.remove()
    raise HTTPException(status_code=501, detail="Not Implemented Yet")

# Add endpoints later for:
# - Reading/Writing .plan files (maybe via docker cp or direct volume access if safe)
# - Listing active projects