import docker
from docker.errors import APIError, NotFound
import logging
from config import DOCKER_SOCKET_PATH, PROJECTS_BASE_DIR
import os

logger = logging.getLogger(__name__)

# Initialize Docker client (could be enhanced with error handling)
# Consider moving initialization to lifespan manager if complex setup needed
try:
    docker_client = docker.from_env(environment={'DOCKER_HOST': DOCKER_SOCKET_PATH})
    # Test connection
    docker_client.ping()
    logger.info(f"Successfully connected to Docker daemon at {DOCKER_SOCKET_PATH}")
except Exception as e:
    logger.error(f"Failed to connect to Docker daemon at {DOCKER_SOCKET_PATH}: {e}", exc_info=True)
    # Decide how to handle this - raise, exit, or run degraded? For now, log and continue.
    docker_client = None

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