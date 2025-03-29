from fastapi import APIRouter, HTTPException, Body, status 
from pydantic import BaseModel, Field
import logging
from services import docker_service # Import our docker functions
from config import DEFAULT_TEST_IMAGE # Import the default image name


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["Projects"])

# --- Pydantic Models for Requests/Responses (Example) ---
# --- Add Pydantic model for the response ---
class HelloWorldResponse(BaseModel):
    project_id: str
    message: str
    container_status: str
    command_exit_code: int | None = None
    command_output: str | None = None

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
# --- NEW Endpoint ---
@router.post(
    "/hello-world",
    summary="Run a simple 'hello world' test project",
    response_model=HelloWorldResponse,
    status_code=status.HTTP_201_CREATED # Use 201 Created for successful resource creation/action
)
async def run_hello_world_project():
    """
    A simple endpoint for testing:
    1. Defines a test project ID and image.
    2. Launches/Starts the corresponding Docker container & volume.
    3. Executes 'echo "hello world..." > /workspace/hello.txt' inside.
    """
    project_id = "crash_test_dummy"
    image_name = DEFAULT_TEST_IMAGE
    hello_command = "sh -c 'echo \"Hello world from MRM36 crash_test_dummy!\" > /workspace/hello.txt'"
    # Using sh -c '...' ensures redirection works reliably via exec

    logger.info(f"Initiating hello-world sequence for project: {project_id}")

    # --- Step 1: Launch/Start Container ---
    try:
        launch_result = await docker_service.launch_project_container(
            project_id=project_id,
            image_name=image_name
        )
        container_status = launch_result.get("status", "unknown")
        logger.info(f"Container launch/start status for {project_id}: {container_status}")
        # Continue even if it was already running

    except ConnectionError as e:
         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Docker connection error: {e}")
    except Exception as e:
        logger.error(f"Failed to create/start project {project_id}: {e}", exc_info=True)
        # Use 500 for unexpected errors during launch
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to launch container: {str(e)}")

    # --- Step 2: Execute Command ---
    command_exit_code = None
    command_output = None
    try:
        exec_result = await docker_service.execute_command_in_container(
            project_id=project_id,
            command=hello_command
        )
        command_exit_code = exec_result.get("exit_code")
        command_output = exec_result.get("output") # Output might be empty for echo redirect
        logger.info(f"Hello command executed for {project_id} with exit code: {command_exit_code}")

        if command_exit_code != 0:
             # Use 500 if the command failed unexpectedly within the container
             raise HTTPException(
                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                 detail=f"Hello command failed inside container (Exit Code: {command_exit_code}). Output: {command_output}"
             )

    except ValueError as e: # Specific error for container not found/running from docker_service
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConnectionError as e:
         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Docker connection error during command execution: {e}")
    except HTTPException:
        # Re-raise exceptions that might have been raised above (like the 500 for non-zero exit code)
        raise
    except Exception as e:
        logger.error(f"Failed to execute command in project {project_id}: {e}", exc_info=True)
        # Use 500 for unexpected errors during execution
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to execute command: {str(e)}")

    # --- Step 3: Return Success Response ---
    return HelloWorldResponse(
        project_id=project_id,
        message="Hello world project sequence completed successfully.",
        container_status=container_status,
        command_exit_code=command_exit_code,
        command_output=command_output # Will likely be empty due to redirect
    )

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