import logging
from urllib.parse import unquote
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from ..models import DownloadRequest
from ..auth import verify_token
from ..clients import alldebrid_client, gofile_client
from ..utils import stream_download

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/download")
async def download_file(
    request: DownloadRequest,
    token: str = Depends(verify_token)
):
    """Download a file from various hosting services"""
    try:
        logger.info(f"Processing download request for: {request.url}")
        url_str = str(request.url)
        
        if "gofile.io" in url_str:
            logger.info("Detected gofile URL, using gofile client")

            async with gofile_client:
                if "/download/web/" in url_str or "file-" in url_str:   
                    logger.info("Direct gofile download URL detected")

                    url_filename = unquote(url_str.split("/")[-1])
                    filename = request.filename or url_filename or "download"
                    
                    quoted_filename = filename.replace('"', '\\"')
                    
                    headers = {
                        "Content-Disposition": f'attachment; filename="{quoted_filename}"',
                        "Content-Type": "application/octet-stream"
                    }
                    
                    return StreamingResponse(
                        gofile_client.stream_download(url_str),
                        headers=headers,
                        media_type="application/octet-stream"
                    )
                
                else:
                    logger.info("Gofile share URL detected")
                    content_id = gofile_client.parse_gofile_url(url_str)
                
                    content_info = await gofile_client.get_content_info(content_id)
                    
                    if content_info["type"] == "folder":
                        raise HTTPException(
                            status_code=400, 
                            detail="This is a gofile folder. Use the /browse endpoint first to see available files."
                        )

                    filename = request.filename or content_info["name"]
                    download_url = content_info["link"]
                    
                    quoted_filename = filename.replace('"', '\\"')
                    
                    headers = {
                        "Content-Disposition": f'attachment; filename="{quoted_filename}"',
                        "Content-Type": "application/octet-stream"
                    }
                    
                    return StreamingResponse(
                        gofile_client.stream_download(download_url),
                        headers=headers,
                        media_type="application/octet-stream"
                    )
        
        else:
            logger.info("Using AllDebrid for URL processing")
            
            unlock_result = await alldebrid_client.unlock_link(url_str)
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