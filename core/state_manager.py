# project_state.py
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# --- In-memory state for project orchestration ---
# Key: project_id, Value: dictionary with orchestration status, etc.
# orchestration_status: 'running', 'halted', 'idle', 'error'
active_projects_state: Dict[str, Dict] = {}
# --- End state ---

# --- Helper functions for internal state ---
def update_project_orchestration_status(project_id: str, status: str):
    if project_id in active_projects_state:
        active_projects_state[project_id]["orchestration_status"] = status
        logger.info(f"Updated orchestration status for project '{project_id}' to '{status}'.")
    else:
        logger.warning(f"Tried to update orchestration status for unknown project '{project_id}'. Initializing.")
        # Initialize if not known - might be needed during reconnect/resume edge cases
        active_projects_state[project_id] = {"orchestration_status": status}

def get_project_orchestration_status(project_id: str) -> Optional[str]:
     project_state = active_projects_state.get(project_id)
     return project_state.get("orchestration_status") if project_state else None

def add_project_to_state(project_id: str, initial_status: str, container_id: Optional[str] = None, container_status: Optional[str] = None):
    """Safely adds or updates a project in the state dictionary."""
    if project_id not in active_projects_state:
        active_projects_state[project_id] = {}
    active_projects_state[project_id]["orchestration_status"] = initial_status
    if container_id:
        active_projects_state[project_id]["container_id"] = container_id
    if container_status:
         active_projects_state[project_id]["container_status"] = container_status
    logger.debug(f"Added/Updated project '{project_id}' in state: {active_projects_state[project_id]}")


def remove_project_from_state(project_id: str):
    """Removes a project from the active state tracking."""
    if project_id in active_projects_state:
        del active_projects_state[project_id]
        logger.info(f"Removed project '{project_id}' from active state.")
    else:
         logger.warning(f"Tried to remove unknown project '{project_id}' from state.")