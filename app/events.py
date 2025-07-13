import logging
from .config import settings
from .clients import alldebrid_client, gofile_client

logger = logging.getLogger(__name__)

async def startup_event():
    """Handle application startup"""
    logger.info("Starting up Debrid Proxy API...")
    
    if not settings.ALLDEBRID_API_KEY:
        logger.error("ALLDEBRID_API_KEY environment variable not set")
        raise Exception("AllDebrid API key required")
    
    try:
        await gofile_client.start_token_refresh_task()
        
        success = await alldebrid_client.authenticate()
        if not success:
            raise Exception("Failed to authenticate with AllDebrid")
        logger.info("AllDebrid authentication successful")
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise

async def shutdown_event():
    """Handle application shutdown"""
    logger.info("Shutting down...")
    await alldebrid_client.close_session()
    await gofile_client.stop_token_refresh_task()
    await gofile_client.close_session() 