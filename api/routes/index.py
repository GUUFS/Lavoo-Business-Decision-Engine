# load the landing page

# import the fastAPI library into
import os

from fastapi import APIRouter

# import the function for rendering the HTML sites
from fastapi.responses import FileResponse, JSONResponse

router = APIRouter(prefix="")

# for the project's static folder done with react.js
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))  # get the absolute path of the file
BASE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(CURRENT_DIR))
)  # get the current directory of the file
OUT_DIR = os.path.join(BASE_DIR, "web")  # get the absolute path of the out folder


@router.get("/{any_path:path}")
def serve_react(any_path: str):
    """Serve the React app for all routes."""
    index_path = os.path.join(OUT_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(status_code=404, content={"message": "index.html not found"})
