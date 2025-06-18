import os
import aiohttp
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl
import logging
from typing import Optional
import uvicorn
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLDEBRID_USERNAME = os.getenv("ALLDEBRID_USERNAME")
ALLDEBRID_PASSWORD = os.getenv("ALLDEBRID_PASSWORD")
API_TOKEN = os.getenv("API_TOKEN")
ALLDEBRID_API_KEY = os.getenv("ALLDEBRID_API_KEY")

app = FastAPI(title="Debrid Proxy API", version="1.0.0")
security = HTTPBearer()

class AllDebridClient:
    def __init__(self):
        self.session = None
        self.api_key = ALLDEBRID_API_KEY
        self.base_url = "https://api.alldebrid.com/v4"
        self.authenticated = False
    
    async def create_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        if self.session:
            await self.session.close()
    
    async def authenticate(self):
        await self.create_session()
        
        if not self.api_key:
            raise Exception("AllDebrid API key not provided")
        
        try: 
            async with self.session.get(
                f"{self.base_url}/user",
                params={"agent": "debrid-proxy", "apikey": self.api_key}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        self.authenticated = True
                        logger.info(f"Successfully authenticated with AllDebrid as user: {data['data']['user']['username']}")
                        return True
                
                logger.error(f"Authentication failed: {await response.text()}")
                return False
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False
    
    async def unlock_link(self, link: str):
        if not self.authenticated:
            await self.authenticate()
        
        if not self.authenticated:
            raise Exception("Not authenticated with AllDebrid")
        
        try:
            async with self.session.get(
                f"{self.base_url}/link/unlock",
                params={
                    "agent": "debrid-proxy",
                    "apikey": self.api_key,
                    "link": link
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        link_data = data["data"]
                        download_url = link_data["link"]
                        filename = link_data.get("filename", "download")
                        logger.info(f"AllDebrid returned filename: {filename}")
                        return {
                            "url": download_url,
                            "filename": filename
                        }
                
                error_text = await response.text()
                logger.error(f"Failed to unlock link: {error_text}")
                raise Exception(f"Failed to unlock link: {error_text}")
        except Exception as e:
            logger.error(f"Error unlocking link: {str(e)}")
            raise

alldebrid_client = AllDebridClient()

class DownloadRequest(BaseModel):
    url: HttpUrl
    filename: Optional[str] = None

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != API_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid authentication token")
    return credentials.credentials

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Debrid Proxy API...")
    
    if not ALLDEBRID_API_KEY:
        logger.error("ALLDEBRID_API_KEY environment variable not set")
        raise Exception("AllDebrid API key required")
    
    try:
        success = await alldebrid_client.authenticate()
        if not success:
            raise Exception("Failed to authenticate with AllDebrid")
        logger.info("AllDebrid authentication successful")
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down...")
    await alldebrid_client.close_session()

async def stream_download(url: str, chunk_size: int = 8192):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise HTTPException(status_code=response.status, detail="Failed to download file")
            
            async for chunk in response.content.iter_chunked(chunk_size):
                yield chunk

@app.get("/")
async def root():
    return {"message": "Debrid Proxy API is running", "status": "healthy"}

@app.post("/download")
async def download_file(
    request: DownloadRequest,
    token: str = Depends(verify_token)
):
    try:
        logger.info(f"Processing download request for: {request.url}")
        
        unlock_result = await alldebrid_client.unlock_link(str(request.url))
        unlocked_url = unlock_result["url"]
        alldebrid_filename = unlock_result["filename"]
        
        logger.info(f"Successfully unlocked link: {unlocked_url}")
        logger.info(f"AllDebrid filename: {alldebrid_filename}")
        
        filename = request.filename or alldebrid_filename or "download"
        
        quoted_filename = filename.replace('"', '\\"')
        
        headers = {
            "Content-Disposition": f'attachment; filename="{quoted_filename}"',
            "Content-Type": "application/octet-stream"
        }
        
        return StreamingResponse(
            stream_download(unlocked_url),
            headers=headers,
            media_type="application/octet-stream"
        )
    except Exception as e:
        logger.error(f"Download failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@app.get("/status")
async def get_status(token: str = Depends(verify_token)):
    return {
        "authenticated": alldebrid_client.authenticated,
        "service": "AllDebrid"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
