import aiohttp
import asyncio
import logging
from fastapi import HTTPException
from ..config import settings

logger = logging.getLogger(__name__)

async def stream_download(url: str, chunk_size: int = None, max_retries: int = None):
    """Stream download with retry and resume capability for AllDebrid URLs"""
    chunk_size = chunk_size or settings.CHUNK_SIZE
    max_retries = max_retries or 10  
    
    timeout = aiohttp.ClientTimeout(
        total=None,
        connect=30,
        sock_read=300
    )
    
    bytes_downloaded = 0
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            headers = {}
            if bytes_downloaded > 0:
                headers['Range'] = f'bytes={bytes_downloaded}-'
                logger.info(f"Resuming download from byte {bytes_downloaded} (attempt {retry_count + 1}/{max_retries + 1})")
            else:
                logger.info(f"Starting download (attempt {retry_count + 1}/{max_retries + 1})")
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status not in [200, 206]:
                        if response.status == 416:
                            logger.error("Range not supported or invalid, cannot resume")
                            raise HTTPException(status_code=500, detail="Cannot resume download - range not supported")
                        raise HTTPException(status_code=response.status, detail=f"Failed to download file: HTTP {response.status}")

                    if bytes_downloaded == 0:
                        content_length = response.headers.get('content-length')
                        if content_length:
                            total_size = int(content_length)
                            logger.info(f"File size: {total_size / (1024*1024):.2f} MB")
                        else:
                            logger.info("File size: unknown")
                    
                    try:
                        async for chunk in response.content.iter_chunked(chunk_size):
                            if chunk:
                                bytes_downloaded += len(chunk)
                                yield chunk
                        
                        logger.info(f"Download completed successfully: {bytes_downloaded / (1024*1024):.2f} MB")
                        return
                        
                    except (aiohttp.ClientPayloadError, aiohttp.ClientConnectionError, asyncio.TimeoutError) as e:
                        logger.warning(f"Download interrupted at {bytes_downloaded / (1024*1024):.2f} MB: {e}")
                        retry_count += 1
                        
                        if retry_count <= max_retries:
                            logger.info(f"Will retry download from byte {bytes_downloaded}")
                            await asyncio.sleep(1)
                            continue
                        else:
                            logger.error(f"Max retries ({max_retries}) exceeded, giving up")
                            return
                    
                    except Exception as e:
                        logger.error(f"Unexpected error during download streaming: {e}")
                        retry_count += 1
                        if retry_count <= max_retries:
                            await asyncio.sleep(1)
                            continue
                        else:
                            return
                            
        except aiohttp.ClientError as e:
            logger.error(f"Client error during download setup (attempt {retry_count + 1}): {e}")
            retry_count += 1
            if retry_count <= max_retries:
                await asyncio.sleep(1)
                continue
            else:
                raise HTTPException(status_code=500, detail="Failed to establish download connection after retries")
        
        except Exception as e:
            logger.error(f"Unexpected error in stream_download (attempt {retry_count + 1}): {e}")
            retry_count += 1
            if retry_count <= max_retries:
                await asyncio.sleep(1)
                continue
            else:
                raise HTTPException(status_code=500, detail=f"Download failed after retries: {str(e)}")
    
    logger.error("Download failed after all retry attempts")
    return 