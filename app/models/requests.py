from pydantic import BaseModel, HttpUrl
from typing import Optional

class DownloadRequest(BaseModel):
    url: HttpUrl
    filename: Optional[str] = None

class BrowseRequest(BaseModel):
    url: HttpUrl
    password: Optional[str] = None 