import aiohttp
import logging
from ..config import settings

logger = logging.getLogger(__name__)

class AllDebridClient:
    def __init__(self):
        self.session = None
        self.api_key = settings.ALLDEBRID_API_KEY
        self.base_url = "https://api.alldebrid.com/v4"
        self.authenticated = False
    
    async def create_session(self):
        """Create aiohttp session"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(
                total=120,
                connect=30,
                sock_read=60
            )
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
    
    async def authenticate(self):
        """Authenticate with AllDebrid using API key"""
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
        """Unlock a link using AllDebrid and return both URL and filename"""
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
        """Use AllDebrid redirector to get redirected links"""
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
        """Get information about multiple links"""
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