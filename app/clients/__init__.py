from .alldebrid import AllDebridClient
from .gofile import GofileClient

alldebrid_client = AllDebridClient()
gofile_client = GofileClient()

__all__ = ["AllDebridClient", "GofileClient", "alldebrid_client", "gofile_client"] 