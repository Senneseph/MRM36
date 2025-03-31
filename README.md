# MRM36
Memory Rotate Multiplicity E-Seek-S

## Setup

# Install Python, Git, and Docker
You will need Python, Git, and Docker.

# Create a virtual environment (if you haven't already)
`python -m venv .venv`

# Activate it on Windows
`.\.venv\Scripts\activate`

# Activate it on OS X / Linux
`source .venv/bin/activate`

## Install necessary libraries
`pip install -r requirements.txt`

## Build basic image
`docker build -t mrm36/base-tools:latest .`

## Launch Service
`uvicorn main:app --host 127.0.0.1 --port 8001 --reload`

# Troubleshooting
> Problem: Application doesn't seem to be processing API commands.
Solution: Check that the port MRM36 uses is not in use by another application. Run `netstat -ano | findstr ":8001"` on Windows (or equivalent on another OS). If something's already using the port, kill its process.