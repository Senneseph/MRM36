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