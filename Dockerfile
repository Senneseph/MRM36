# Dockerfile (for the MRM36 API Service)

# Use a suitable Python base image
FROM python:3.12-slim

# Set environment variables to prevent buffering issues with logs
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Copy only the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port the application runs on (matches Uvicorn command)
EXPOSE 8001

# Default command to run the application using Uvicorn
# Use 0.0.0.0 to listen on all interfaces inside the container
# Remove --reload for production, keep for development if desired
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]