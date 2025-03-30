import docker
from docker.errors import APIError, NotFound, DockerException
import logging
from config import DOCKER_SOCKET_PATH, PROJECTS_BASE_DIR
import os
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# --- Docker Client Initialization ---
docker_client: Optional[docker.DockerClient] = None
try:
    # Explicitly provide base_url, helps avoid ambiguity
    docker_client = docker.DockerClient(base_url=DOCKER_SOCKET_PATH)
    docker_client.ping() # Test connection
    logger.info(f"Successfully connected to Docker daemon at {DOCKER_SOCKET_PATH}")
except Exception as e:
    logger.error(f"Failed to connect to Docker daemon at {DOCKER_SOCKET_PATH}: {e}", exc_info=False)
    # Set client to None so other functions can check
    docker_client = None

# --- Helper ---
def get_container_name(project_id: str) -> str:
    return f"mrm36_project_{project_id}"

def get_volume_name(project_id: str) -> str:
    return f"mrm36_project_{project_id}_vol"

# --- Existing Functions (Ensure Robustness) ---
async def launch_project_container(project_id: str, image_name: str) -> Dict:
    # ... (Keep existing logic, ensure it handles already running/stopped states) ...
    # Make sure it raises ConnectionError if docker_client is None
    if not docker_client:
        raise ConnectionError("Docker client not available.")
    # ... (rest of the function) ...
    # Return dict like {"status": ..., "container_id": ..., "workspace_volume": ...}

async def execute_command_in_container(project_id: str, command: str) -> Dict:
    # ... (Keep existing logic) ...
    # Make sure it raises ConnectionError if docker_client is None
    if not docker_client:
        raise ConnectionError("Docker client not available.")
    # ... (rest of the function) ...
    # Return dict like {"exit_code": ..., "output": ...}

# --- NEW Functions ---
async def stop_project_container(project_id: str) -> bool:
    """Stops the container for a given project ID."""
    if not docker_client:
        raise ConnectionError("Docker client not available.")
    container_name = get_container_name(project_id)
    try:
        container = docker_client.containers.get(container_name)
        if container.status == 'running':
            logger.info(f"Stopping container '{container_name}'...")
            container.stop()
            logger.info(f"Container '{container_name}' stopped.")
            return True
        else:
            logger.info(f"Container '{container_name}' is already stopped (status: {container.status}).")
            return True # Considered success if already stopped
    except NotFound:
        logger.warning(f"Container '{container_name}' not found, cannot stop.")
        return False # Indicate container wasn't found
    except APIError as e:
        logger.error(f"Docker API error stopping container {container_name}: {e}", exc_info=True)
        raise RuntimeError(f"Docker error stopping container: {e}") from e
    except Exception as e:
         logger.error(f"Unexpected error stopping container {container_name}: {e}", exc_info=True)
         raise RuntimeError(f"Unexpected error stopping container: {e}") from e

async def remove_project_container(project_id: str) -> bool:
    """
    Stops (if running) and removes the container for a given project ID.
    Does NOT remove the associated volume.
    """
    if not docker_client:
        raise ConnectionError("Docker client not available.")
    container_name = get_container_name(project_id)
    try:
        container = docker_client.containers.get(container_name)
        # Ensure stopped before removal
        if container.status == 'running':
            logger.info(f"Container '{container_name}' is running. Stopping before removal...")
            container.stop()
            logger.info(f"Container '{container_name}' stopped.")

        logger.info(f"Removing container '{container_name}'...")
        container.remove() # Set v=True to remove associated anonymous volumes, but we use named ones
        logger.info(f"Container '{container_name}' removed.")
        return True
    except NotFound:
        logger.warning(f"Container '{container_name}' not found, cannot remove.")
        return False # Indicate container wasn't found
    except APIError as e:
        logger.error(f"Docker API error removing container {container_name}: {e}", exc_info=True)
        raise RuntimeError(f"Docker error removing container: {e}") from e
    except Exception as e:
         logger.error(f"Unexpected error removing container {container_name}: {e}", exc_info=True)
         raise RuntimeError(f"Unexpected error removing container: {e}") from e

async def list_mrm36_containers() -> List[Dict]:
    """Lists all Docker containers matching the MRM36 naming convention."""
    if not docker_client:
        logger.warning("Docker client not available, cannot list containers.")
        return [] # Return empty list if no client

    mrm36_containers = []
    try:
        # List all containers (including stopped ones)
        all_containers = docker_client.containers.list(all=True, filters={"name": "mrm36_project_*"})
        for container in all_containers:
            # Extract project ID from name
            if container.name.startswith("mrm36_project_"):
                project_id = container.name.replace("mrm36_project_", "", 1)
                mrm36_containers.append({
                    "project_id": project_id,
                    "container_id": container.short_id,
                    "container_name": container.name,
                    "status": container.status, # e.g., 'running', 'exited', 'created'
                    "image": container.image.tags[0] if container.image.tags else 'unknown'
                })
        logger.info(f"Found {len(mrm36_containers)} MRM36 containers.")
        return mrm36_containers
    except APIError as e:
        logger.error(f"Docker API error listing containers: {e}", exc_info=True)
        # Decide how to handle - maybe return empty list or raise? Returning empty for now.
        return []
    except Exception as e:
        logger.error(f"Unexpected error listing containers: {e}", exc_info=True)
        return []

def ensure_projects_base_dir():
    """Creates the base directory for project volumes if it doesn't exist."""
    os.makedirs(PROJECTS_BASE_DIR, exist_ok=True)
    logger.info(f"Ensured projects base directory exists: {PROJECTS_BASE_DIR}")

# Call this once at startup maybe?
ensure_projects_base_dir()

async def launch_project_container(project_id: str, image_name: str):
    """
    Launches a Docker container for a specific project.
    - Mounts a persistent volume for the workspace.
    - Uses the specified image.
    - Keeps the container running in the background (detached).
    """
    if not docker_client:
        raise ConnectionError("Docker client not available.")

    container_name = f"mrm36_project_{project_id}"
    volume_name = f"mrm36_project_{project_id}_vol"
    workspace_path_in_container = "/workspace"

    try:
        # Check if container already exists
        try:
            container = docker_client.containers.get(container_name)
            if container.status == 'running':
                logger.info(f"Container '{container_name}' is already running.")
                return {"status": "already_running", "container_id": container.id, "workspace_volume": volume_name}
            elif container.status == 'exited':
                 logger.info(f"Container '{container_name}' exists but is stopped. Starting...")
                 container.start()
                 return {"status": "started_existing", "container_id": container.id, "workspace_volume": volume_name}
            # Handle other statuses if needed (created, paused, etc.)

        except NotFound:
             logger.info(f"Container '{container_name}' not found. Creating...")

        # Ensure the image exists locally, pull if necessary (optional, can be slow)
        # try:
        #     docker_client.images.get(image_name)
        # except docker.errors.ImageNotFound:
        #     logger.info(f"Pulling image '{image_name}'...")
        #     docker_client.images.pull(image_name)

        # Create persistent volume (Docker manages this, typically under /var/lib/docker/volumes)
        try:
            volume = docker_client.volumes.get(volume_name)
            logger.info(f"Using existing volume '{volume_name}'")
        except NotFound:
            logger.info(f"Creating new volume '{volume_name}'")
            volume = docker_client.volumes.create(name=volume_name)

        # Define volume mount
        mounts = [
            docker.types.Mount(
                target=workspace_path_in_container,
                source=volume_name,
                type='volume'
            )
        ]

        # Create and start the container
        # Use 'sleep infinity' or a similar command to keep it running idly
        container = docker_client.containers.run(
            image=image_name,
            name=container_name,
            detach=True, # Run in background
            tty=True,    # Keep stdin open even if not attached (needed for exec)
            stdin_open=True, # Keep stdin open
            command="sleep infinity", # Keep container running
            mounts=mounts,
            # Add network settings, resource limits, etc. as needed
            restart_policy={"Name": "unless-stopped"} # Optional: auto-restart
        )
        logger.info(f"Successfully created and started container '{container_name}' ({container.short_id})")
        return {"status": "created", "container_id": container.id, "workspace_volume": volume_name}

    except APIError as e:
        logger.error(f"Docker API error launching container for project {project_id}: {e}", exc_info=True)
        raise RuntimeError(f"Docker error: {e}") from e
    except Exception as e:
         logger.error(f"Unexpected error launching container for project {project_id}: {e}", exc_info=True)
         raise RuntimeError(f"Unexpected error: {e}") from e

async def execute_command_in_container(project_id: str, command: str):
    """Executes a command inside the project's running container."""
    if not docker_client:
        raise ConnectionError("Docker client not available.")

    container_name = f"mrm36_project_{project_id}"
    try:
        container = docker_client.containers.get(container_name)
        if container.status != 'running':
            # Optionally try to start it? Or just fail.
             raise ValueError(f"Container '{container_name}' is not running (status: {container.status}).")

        logger.info(f"Executing command in '{container_name}': {command}")
        # Execute command within the container's workspace directory
        # Use workdir parameter in exec_run
        exit_code, output = container.exec_run(cmd=command, workdir="/workspace", stream=False, demux=False)
        output_str = output.decode('utf-8') if output else ""

        logger.info(f"Command in '{container_name}' finished with exit code {exit_code}.")
        return {"exit_code": exit_code, "output": output_str}

    except NotFound:
        logger.error(f"Container '{container_name}' not found for command execution.")
        raise ValueError(f"Project container '{container_name}' not found.")
    except APIError as e:
        logger.error(f"Docker API error executing command in {container_name}: {e}", exc_info=True)
        raise RuntimeError(f"Docker error: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error executing command in {container_name}: {e}", exc_info=True)
        raise RuntimeError(f"Unexpected error: {e}") from e


async def copy_to_container(project_id: str, src_path_host: str, dest_path_container: str):
    """Copies a file or directory from the host to the container's workspace."""
    # Implementation using container.put_archive()
    # Note: put_archive requires a tar stream.
    logger.warning(f"copy_to_container for project {project_id} not fully implemented.")
    pass

async def copy_from_container(project_id: str, src_path_container: str, dest_path_host: str):
    """Copies a file or directory from the container's workspace to the host."""
    # Implementation using container.get_archive()
    # Note: get_archive returns a tar stream that needs processing.
    logger.warning(f"copy_from_container for project {project_id} not fully implemented.")
    pass