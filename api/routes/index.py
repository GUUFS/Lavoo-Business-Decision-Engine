# load the landing page

# import the fastAPI library into
import os

from fastapi import APIRouter

# import the function for rendering the HTML sites
from fastapi.responses import FileResponse, JSONResponse

router = APIRouter(prefix="")

# for the project's static folder done with react.js
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(CURRENT_DIR)))
OUT_DIR = os.path.join(BASE_DIR, "web")


@router.get("/{any_path:path}")
def serve_react(any_path: str):
    """Serve the React app for all routes, except API routes."""
    
    # Don't serve index.html for API routes - let them 404 properly
    if any_path.startswith("api/"):
        return JSONResponse(status_code=404, content={"message": "API endpoint not found"})
    
    # Check if a static file exists at this path
    file_path = os.path.join(OUT_DIR, any_path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # Otherwise serve index.html (for React Router)
    index_path = os.path.join(OUT_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    return JSONResponse(status_code=404, content={"message": "index.html not found"})