import httpx
from fastapi import APIRouter, HTTPException, Depends
import logging
from config import OLLAMA_API_BASE_URL

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ollama", tags=["Ollama"])

# Dependency to get the shared client (if initialized in lifespan)
# Or initialize a client here if preferred
# For simplicity now, assume client is globally accessible or passed differently.
# Let's refine this dependency injection later if needed.
# For now, create a client per request (less efficient but simple)
async def get_ollama_client():
     # In real app use shared client from app.state or lifespan
    async with httpx.AsyncClient(base_url=OLLAMA_API_BASE_URL, timeout=10.0) as client:
        yield client


@router.get("/status", summary="Check connection status to Ollama")
async def get_ollama_status(client: httpx.AsyncClient = Depends(get_ollama_client)):
    """Checks connectivity to the configured Ollama API endpoint."""
    try:
        response = await client.get("/tags")
        response.raise_for_status()
        logger.info("Successfully connected to Ollama.")
        return {"status": "connected", "ollama_url": OLLAMA_API_BASE_URL}
    # Keep error handling as before...
    except httpx.ConnectError as e:
        logger.error(f"Ollama connection failed: {e}")
        raise HTTPException(status_code=503, detail=f"Could not connect to Ollama at {OLLAMA_API_BASE_URL}.")
    except Exception as e:
        logger.exception("Unexpected error checking Ollama status")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@router.get("/models", summary="List available Ollama models")
async def get_ollama_models(client: httpx.AsyncClient = Depends(get_ollama_client)):
    """Retrieves the list of models available locally in the Ollama instance."""
    try:
        response = await client.get("/tags")
        response.raise_for_status()
        models_data = response.json()
        return {"models": models_data.get("models", [])}
    # Keep error handling as before...
    except httpx.ConnectError as e:
        logger.error(f"Ollama connection failed fetching models: {e}")
        raise HTTPException(status_code=503, detail=f"Could not connect to Ollama at {OLLAMA_API_BASE_URL}.")
    except Exception as e:
        logger.exception("Unexpected error fetching Ollama models")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")