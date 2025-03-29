# config.py
import os
import platform # Import the platform module

# Basic configuration settings
OLLAMA_API_BASE_URL = os.getenv("OLLAMA_API_BASE_URL", "http://localhost:11434/api")
OLLAMA_TIMEOUT = 10.0

# --- Dynamically set Docker socket path based on OS ---
DEFAULT_DOCKER_SOCKET_PATH = (
    "npipe:////./pipe/docker_engine" if platform.system() == "Windows"
    else "unix://var/run/docker.sock" # Default for Linux/macOS
)
DOCKER_SOCKET_PATH = os.getenv("DOCKER_SOCKET_PATH", DEFAULT_DOCKER_SOCKET_PATH)
# --- End of dynamic setting ---

API_HOST = "127.0.0.1"
API_PORT = 8001 # Use the port you were running on

PROJECTS_BASE_DIR = os.getenv("PROJECTS_BASE_DIR", "./mrm36_projects")

print(f"Attempting to use Docker Host: {DOCKER_SOCKET_PATH}") # Add print for debugging