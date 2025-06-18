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
    
    async def redirector(self, link: str):
        if not self.authenticated:
            await self.authenticate()
        
        if not self.authenticated:
            raise Exception("Not authenticated with AllDebrid")
        
        try:
            form_data = aiohttp.FormData()
            form_data.add_field('link', link)
            
            async with self.session.post(
                f"{self.base_url}/link/redirector",
                headers={"Authorization": f"Bearer {self.api_key}"},
                data=form_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        return data["data"]
                
                error_text = await response.text()
                logger.error(f"Redirector failed: {error_text}")
                raise Exception(f"Redirector failed: {error_text}")
        except Exception as e:
            logger.error(f"Error in redirector: {str(e)}")
            raise
    
    async def get_link_infos(self, links: list, password: str = None):
        if not self.authenticated:
            await self.authenticate()
        
        if not self.authenticated:
            raise Exception("Not authenticated with AllDebrid")
        
        try:
            form_data = aiohttp.FormData()
            
            for link in links:
                form_data.add_field('link[]', link)
            
            if password:
                form_data.add_field('password', password)
            
            async with self.session.post(
                f"{self.base_url}/link/infos",
                headers={"Authorization": f"Bearer {self.api_key}"},
                data=form_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        return data["data"]
                
                error_text = await response.text()
                logger.error(f"Link infos failed: {error_text}")
                raise Exception(f"Link infos failed: {error_text}")
        except Exception as e:
            logger.error(f"Error getting link infos: {str(e)}")
            raise

alldebrid_client = AllDebridClient()

class DownloadRequest(BaseModel):
    url: HttpUrl
    filename: Optional[str] = None

class BrowseRequest(BaseModel):
    url: HttpUrl
    password: Optional[str] = None

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

@app.post("/browse")
async def browse_link(
    request: BrowseRequest,
    token: str = Depends(verify_token)
):
    try:
        logger.info(f"Processing browse request for: {request.url}")
        
        redirector_result = await alldebrid_client.redirector(str(request.url))
        logger.info(f"Redirector returned: {redirector_result}")

        redirected_links = []
        if isinstance(redirector_result, dict):
            if 'links' in redirector_result:
                redirected_links = redirector_result['links']
            elif 'link' in redirector_result:
                redirected_links = [redirector_result['link']]
            else:
                redirected_links = [redirector_result]
        elif isinstance(redirector_result, list):
            redirected_links = redirector_result
        else:
            redirected_links = [redirector_result]
        
        if not redirected_links:
            return {"error": "No links found in redirector response", "files": []}
        
        logger.info(f"Found {len(redirected_links)} redirected links")
        
        infos_result = await alldebrid_client.get_link_infos(
            redirected_links, 
            request.password
        )
        
        logger.info(f"Infos result type: {type(infos_result)}")
        logger.info(f"Infos result keys: {infos_result.keys() if isinstance(infos_result, dict) else 'Not a dict'}")
        logger.info(f"Infos result sample: {str(infos_result)[:500]}...") 
        
        infos_list = []
        if isinstance(infos_result, dict) and 'infos' in infos_result:
            infos_list = infos_result['infos']
        elif isinstance(infos_result, list):
            infos_list = infos_result
        
        logger.info(f"Link infos returned: {len(infos_list)} items")
        
        files = []
        for info in infos_list:
            if isinstance(info, dict):
                size_bytes = info.get("size", 0)
                size_human = info.get("size_human", "")
                if not size_human and size_bytes > 0:
                    if size_bytes >= 1024**3:
                        size_human = f"{size_bytes / (1024**3):.2f} GB"
                    elif size_bytes >= 1024**2:
                        size_human = f"{size_bytes / (1024**2):.2f} MB"
                    elif size_bytes >= 1024:
                        size_human = f"{size_bytes / 1024:.2f} KB"
                    else:
                        size_human = f"{size_bytes} B"
                
                file_info = {
                    "filename": info.get("filename", "unknown"),
                    "size": size_bytes,
                    "size_human": size_human,
                    "link": info.get("link", ""),
                    "host": info.get("host", "unknown"),
                    "hostDomain": info.get("hostDomain", "unknown"),
                    "supported": True
                }
                files.append(file_info)
        
        return {
            "url": str(request.url),
            "total_files": len(files),
            "files": files,
            "password_protected": bool(request.password)
        }
        
    except Exception as e:
        logger.error(f"Browse failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Browse failed: {str(e)}")

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
