# config.py
import os
import platform

# Basic configuration settings
OLLAMA_API_BASE_URL = os.getenv("OLLAMA_API_BASE_URL", "http://localhost:11434/api")
OLLAMA_TIMEOUT = 10.0

# Docker connection
DEFAULT_DOCKER_SOCKET_PATH = "unix://var/run/docker.sock"
DOCKER_SOCKET_PATH = os.getenv("DOCKER_SOCKET_PATH", DEFAULT_DOCKER_SOCKET_PATH)

# API Server
API_HOST = "127.0.0.1"
API_PORT = 8001

# Project Management
PROJECTS_BASE_DIR = os.getenv("PROJECTS_BASE_DIR", "./mrm36_projects")
DEFAULT_TEST_IMAGE = "mrm36/base-tools:latest"

# --- NEW: Restart Behavior ---
# Attempt to reconnect to existing MRM36 containers on startup?
RECONNECT_PROJECTS = os.getenv("RECONNECT_PROJECTS", "True").lower() in ('true', '1', 't')
# If reconnecting, automatically resume orchestration based on .plan state?
# If False, projects reconnect but remain idle until explicitly resumed.
RESUME_PROJECTS = os.getenv("RESUME_PROJECTS", "True").lower() in ('true', '1', 't')
# --- End New ---

print(f"Attempting to use Docker Host: {DOCKER_SOCKET_PATH}")
print(f"Reconnect Projects on Startup: {RECONNECT_PROJECTS}")
print(f"Resume Reconnected Projects: {RESUME_PROJECTS}")