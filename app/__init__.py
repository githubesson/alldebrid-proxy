from fastapi import FastAPI
from fastapi.security import HTTPBearer

from .config import settings
from .routes import download, browse, status
from .events import startup_event, shutdown_event

app = FastAPI(title="Debrid Proxy API", version="1.0.0")
security = HTTPBearer()


app.add_event_handler("startup", startup_event)
app.add_event_handler("shutdown", shutdown_event)


app.include_router(download.router)
app.include_router(browse.router)
app.include_router(status.router)

@app.get("/")
async def root():
    return {"message": "Debrid Proxy API is running", "status": "healthy"} 