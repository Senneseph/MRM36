# Use a specific LTS version for reproducibility
FROM ubuntu:22.04

# Avoid interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install common development tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    # Basics
    git \
    curl \
    wget \
    unzip \
    jq \
    ca-certificates \
    # Text Editors
    nano \
    vim \
    # Build Tools
    build-essential \
    cmake \
    # Python
    python3 \
    python3-pip \
    python3-venv \
    # Node.js (Example - choose version as needed)
    # nodejs \
    # npm \
    # Add other languages/tools as needed (e.g., Go, Rust, Java SDK)
    # ... \
    # Clean up apt cache
    && rm -rf /var/lib/apt/lists/*

# Set a default working directory (optional)
WORKDIR /workspace

# (Optional) Create a non-root user for added security
# RUN useradd -ms /bin/bash agentuser
# USER agentuser

# Default command (will be overridden by 'sleep infinity' when run by service)
CMD ["/bin/bash"]