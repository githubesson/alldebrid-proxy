import aiohttp
import asyncio
import logging
from hashlib import sha256
from typing import Dict, Any
from ..config import settings

logger = logging.getLogger(__name__)

class GofileClient:
    def __init__(self):
        self.session = None
        self.token = None
        self.authenticated = False
    
    async def create_session(self):
        """Create aiohttp session"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
    
    async def get_token(self):
        """Get gofile access token by creating anonymous account"""
        await self.create_session()
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "*/*",
            "Connection": "keep-alive",
        }
        
        try:
            async with self.session.post("https://api.gofile.io/accounts", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "ok":
                        self.token = data["data"]["token"]
                        self.authenticated = True
                        logger.info("Successfully created gofile anonymous account")
                        return True
                
                logger.error(f"Failed to create gofile account: {await response.text()}")
                return False
        except Exception as e:
            logger.error(f"Error creating gofile account: {str(e)}")
            return False
    
    async def get_content_info(self, content_id: str, password: str = None):
        """Get information about gofile content"""
        if not self.authenticated:
            await self.get_token()
        
        if not self.authenticated:
            raise Exception("Failed to authenticate with gofile")
        
        url = f"https://api.gofile.io/contents/{content_id}?wt=4fd6sg89d7s6&cache=true"
        if password:
            
            password_hash = sha256(password.encode()).hexdigest()
            url = f"{url}&password={password_hash}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "*/*",
            "Connection": "keep-alive",
            "Authorization": f"Bearer {self.token}",
        }
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "ok":
                        return data["data"]
                
                error_text = await response.text()
                logger.error(f"Failed to get gofile content info: {error_text}")
                raise Exception(f"Failed to get gofile content info: {error_text}")
        except Exception as e:
            logger.error(f"Error getting gofile content info: {str(e)}")
            raise
    
    def parse_gofile_url(self, url: str):
        """Parse gofile URL to extract content ID"""
        try:
            
            if "/d/" not in url:
                raise Exception("Invalid gofile URL format")
            
            content_id = url.split("/")[-1]
            if not content_id:
                raise Exception("No content ID found in URL")
            
            return content_id
        except Exception as e:
            logger.error(f"Error parsing gofile URL: {str(e)}")
            raise
    
    async def get_files_list(self, content_id: str, password: str = None):
        """Get list of files from gofile content (recursive for folders)"""
        content_info = await self.get_content_info(content_id, password)
        
        if "password" in content_info and "passwordStatus" in content_info:
            if content_info["passwordStatus"] != "passwordOk":
                raise Exception("Password required or incorrect password")
        
        files = []
        
        if content_info["type"] == "folder":
            
            await self._parse_folder_recursive(content_info, files, password)
        else:
            
            files.append({
                "filename": content_info["name"],
                "size": content_info.get("size", 0),
                "link": content_info["link"],
                "id": content_id
            })
        
        return files
    
    async def _parse_folder_recursive(self, folder_data: Dict[str, Any], files: list, password: str = None, path_prefix: str = ""):
        """Recursively parse folder contents"""
        for child_id, child in folder_data.get("children", {}).items():
            if child["type"] == "folder":
                
                folder_info = await self.get_content_info(child["id"], password)
                folder_path = f"{path_prefix}{child['name']}/" if path_prefix else f"{child['name']}/"
                await self._parse_folder_recursive(folder_info, files, password, folder_path)
            else:
                
                files.append({
                    "filename": f"{path_prefix}{child['name']}" if path_prefix else child['name'],
                    "size": child.get("size", 0),
                    "link": child["link"],
                    "id": child["id"]
                })
    
    async def stream_download(self, download_url: str, chunk_size: int = None, max_retries: int = None):
        """Stream download gofile content with resume capability"""
        if not self.authenticated:
            await self.get_token()
        
        chunk_size = chunk_size or settings.CHUNK_SIZE
        max_retries = max_retries or settings.MAX_RETRIES
        
        bytes_downloaded = 0
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                headers = {
                    "Cookie": f"accountToken={self.token}",
                    "Accept-Encoding": "gzip, deflate, br",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "*/*",
                    "Referer": download_url,
                    "Origin": "https://gofile.io",
                    "Connection": "keep-alive",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-site",
                    "Pragma": "no-cache",
                    "Cache-Control": "no-cache"
                }
                
                
                if bytes_downloaded > 0:
                    headers['Range'] = f'bytes={bytes_downloaded}-'
                    logger.info(f"Resuming gofile download from byte {bytes_downloaded}")
                
                async with self.session.get(download_url, headers=headers) as response:
                    
                    if response.status not in [200, 206]:
                        if response.status in [403, 404, 405, 500]:
                            raise Exception(f"Gofile download failed: HTTP {response.status}")
                        raise Exception(f"Unexpected HTTP status: {response.status}")
                    
                    
                    if bytes_downloaded == 0:
                        content_length = response.headers.get('content-length')
                        if content_length:
                            logger.info(f"Starting gofile download: {int(content_length) / (1024*1024):.2f} MB")
                        else:
                            logger.info("Starting gofile download (unknown size)")
                    
                    try:
                        async for chunk in response.content.iter_chunked(chunk_size):
                            if chunk:
                                bytes_downloaded += len(chunk)
                                yield chunk
                        
                        
                        logger.info(f"Gofile download completed: {bytes_downloaded / (1024*1024):.2f} MB")
                        return
                        
                    except (aiohttp.ClientPayloadError, aiohttp.ClientConnectionError, asyncio.TimeoutError) as e:
                        logger.warning(f"Gofile download interrupted at {bytes_downloaded / (1024*1024):.2f} MB: {e}")
                        retry_count += 1
                        
                        if retry_count <= max_retries:
                            logger.info(f"Will retry gofile download from byte {bytes_downloaded}")
                            await asyncio.sleep(1)
                            continue
                        else:
                            logger.error(f"Gofile download max retries ({max_retries}) exceeded")
                            return
                    
                    except Exception as e:
                        logger.error(f"Unexpected error during gofile download: {e}")
                        retry_count += 1
                        if retry_count <= max_retries:
                            await asyncio.sleep(1)
                            continue
                        else:
                            return
                            
            except Exception as e:
                logger.error(f"Error setting up gofile download (attempt {retry_count + 1}): {e}")
                retry_count += 1
                if retry_count <= max_retries:
                    await asyncio.sleep(1)
                    continue
                else:
                    from fastapi import HTTPException
                    raise HTTPException(status_code=500, detail=f"Gofile download failed after retries: {str(e)}")
        
        logger.error("Gofile download failed after all retry attempts")
        return 