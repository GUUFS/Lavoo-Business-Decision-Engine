# api/main.py
from fastapi import FastAPI
from api.routes import ai  # Import the ai router

app = FastAPI(title="AI Business Analyst", description="API for AI tool recommendations and business insights")

# Include the ai router
app.include_router(ai.router, prefix="/api", tags=["ai"])

@app.get("/")
async def read_root():
    return {"message": "Welcome to the AI Business Analyst API!"}