import logging
from fastapi import APIRouter, HTTPException, Depends

from ..models import BrowseRequest
from ..auth import verify_token
from ..clients import alldebrid_client, gofile_client

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/browse")
async def browse_link(
    request: BrowseRequest,
    token: str = Depends(verify_token)
):
    """Browse files in a link/folder before downloading"""
    try:
        logger.info(f"Processing browse request for: {request.url}")
        url_str = str(request.url)
        
        if "gofile.io" in url_str:
            logger.info("Detected gofile URL, using gofile client")
            
            async with gofile_client:
                content_id = gofile_client.parse_gofile_url(url_str)
                
                files_list = await gofile_client.get_files_list(content_id, request.password)
                
                files = []
                for file_info in files_list:
                    size_bytes = file_info.get("size", 0)
                    size_human = ""
                    if size_bytes > 0:
                        if size_bytes >= 1024**3:
                            size_human = f"{size_bytes / (1024**3):.2f} GB"
                        elif size_bytes >= 1024**2:
                            size_human = f"{size_bytes / (1024**2):.2f} MB"
                        elif size_bytes >= 1024:
                            size_human = f"{size_bytes / 1024:.2f} KB"
                        else:
                            size_human = f"{size_bytes} B"
                    
                    files.append({
                        "filename": file_info["filename"],
                        "size": size_bytes,
                        "size_human": size_human,
                        "link": file_info["link"],
                        "host": "gofile.io",
                        "hostDomain": "gofile.io",
                        "supported": True,
                        "id": file_info.get("id", "")
                    })
                
                return {
                    "url": url_str,
                    "total_files": len(files),
                    "files": files,
                    "password_protected": bool(request.password),
                    "service": "gofile"
                }
        
        else:
            logger.info("Using AllDebrid for URL processing")
            
            redirector_result = await alldebrid_client.redirector(url_str)
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
                "url": url_str,
                "total_files": len(files),
                "files": files,
                "password_protected": bool(request.password),
                "service": "alldebrid"
            }
        
    except Exception as e:
        logger.error(f"Browse failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Browse failed: {str(e)}") 