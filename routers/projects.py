from fastapi import APIRouter, HTTPException, Body, status 
from pydantic import BaseModel, Field
import logging
from services import docker_service # Import our docker functions
from config import DEFAULT_TEST_IMAGE # Import the default image name
# Import helper functions from main (consider moving state logic later)
from core.state_manager import (
    active_projects_state,
    update_project_orchestration_status,
    get_project_orchestration_status,
    remove_project_from_state # Import the remove function too
)

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

@router.post(
    "/{project_id}/halt",
    summary="Halt active orchestration for a project",
    status_code=status.HTTP_200_OK
)
async def halt_project_work(project_id: str):
    """
    Signals the orchestrator to stop assigning new tasks or executing
    commands for this project. Does NOT stop the container.
    Work can be resumed later.
    """
    if project_id not in active_projects_state:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found or not active.")
    update_project_orchestration_status(project_id, "halted")
    # TODO: Signal the actual orchestrator/background task for this project if running
    return {"project_id": project_id, "orchestration_status": "halted"}

@router.post(
    "/{project_id}/resume",
    summary="Resume active orchestration for a project",
    status_code=status.HTTP_200_OK
)
async def resume_project_work(project_id: str):
    """
    Signals the orchestrator to resume assigning tasks and executing
    commands for this project based on its .plan file.
    """
    if project_id not in active_projects_state:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found or not active.")
    # Add logic here: check if container is running? Or let orchestrator handle it?
    # For now, just update the flag.
    update_project_orchestration_status(project_id, "running")
    # TODO: Signal the actual orchestrator/background task for this project
    return {"project_id": project_id, "orchestration_status": "running"}

@router.post(
    "/halt-all",
    summary="Halt active orchestration for ALL active projects",
    status_code=status.HTTP_200_OK
)
async def halt_all_projects():
    """Halts orchestration for all currently tracked projects."""
    halted_projects = []
    for project_id in list(active_projects_state.keys()): # Iterate over keys copy
        update_project_orchestration_status(project_id, "halted")
        halted_projects.append(project_id)
        # TODO: Signal orchestrators/tasks
    logger.info(f"Halted orchestration for projects: {halted_projects}")
    return {"message": "Sent halt signal to all active projects.", "halted_count": len(halted_projects)}

@router.post(
    "/resume-all",
    summary="Resume active orchestration for ALL active projects",
    status_code=status.HTTP_200_OK
)
async def resume_all_projects():
    """Resumes orchestration for all currently tracked projects."""
    resumed_projects = []
    for project_id in list(active_projects_state.keys()): # Iterate over keys copy
        update_project_orchestration_status(project_id, "running")
        resumed_projects.append(project_id)
        # TODO: Signal orchestrators/tasks
    logger.info(f"Resumed orchestration for projects: {resumed_projects}")
    return {"message": "Sent resume signal to all active projects.", "resumed_count": len(resumed_projects)}


@router.post(
    "/{project_id}/stop-container",
    summary="Stop the Docker container for a project",
    status_code=status.HTTP_200_OK
)
async def stop_project_container_endpoint(project_id: str):
    """Stops the project's Docker container. Implies halting work."""
    update_project_orchestration_status(project_id, "halted") # Halt orchestration first
    # TODO: Signal orchestrator/task
    try:
        stopped = await docker_service.stop_project_container(project_id)
        if stopped:
             if project_id in active_projects_state:
                 active_projects_state[project_id]["container_status"] = "exited" # Update internal state
             return {"project_id": project_id, "message": "Container stop request sent successfully."}
        else:
             # Container might already be stopped or not found
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Container for project '{project_id}' not found or already stopped.")
    except ConnectionError as e:
         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Docker connection error: {e}")
    except Exception as e:
        logger.error(f"Failed to stop container for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# --- Modify DELETE Endpoint ---
# Changed path to be more specific
@router.delete(
    "/{project_id}/container",
    summary="Stop and Remove a Project's Container (Keeps Volume)",
    status_code=status.HTTP_200_OK # Or 204 No Content
)
async def remove_project_container_endpoint(project_id: str):
    """
    Stops (if running) and removes the project's Docker container.
    The persistent data volume (workspace, .plan, .brain) is KEPT.
    """
    update_project_orchestration_status(project_id, "halted") # Halt orchestration first
    # TODO: Signal orchestrator/task
    try:
        removed = await docker_service.remove_project_container(project_id)
        if removed:
             # Remove from active state tracking if successful
             if project_id in active_projects_state:
                 del active_projects_state[project_id]
             return {"project_id": project_id, "message": "Container removed successfully. Volume data retained."}
        else:
             # Container might have already been removed
             if project_id in active_projects_state:
                 del active_projects_state[project_id] # Clean up state anyway
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Container for project '{project_id}' not found.")
    except ConnectionError as e:
         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Docker connection error: {e}")
    except Exception as e:
        logger.error(f"Failed to remove container for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# Add endpoints later for:
# - Reading/Writing .plan files (maybe via docker cp or direct volume access if safe)
# - Listing active projects