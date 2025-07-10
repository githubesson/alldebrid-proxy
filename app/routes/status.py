from fastapi import APIRouter, Depends

from ..auth import verify_token
from ..clients import alldebrid_client, gofile_client

router = APIRouter()

@router.get("/status")
async def get_status(token: str = Depends(verify_token)):
    """Get status of all services"""
    return {
        "alldebrid": {
            "authenticated": alldebrid_client.authenticated,
            "service": "AllDebrid"
        },
        "gofile": {
            "authenticated": gofile_client.authenticated,
            "service": "Gofile"
        }
    } 