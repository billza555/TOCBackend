from fastapi import FastAPI
import uvicorn
from modules.songs.controller import router as song_router
from core.config import Config

# Create FastAPI app
app = FastAPI(
    title="Music Scraper API",
    description="API for scraping songs, lyrics, and chord images",
    version="1.0.0"
)

# Include routers
app.include_router(song_router)

@app.get("/")
def root():
    """Root endpoint"""
    return {"message": "Music Scraper API", "version": "1.0.0"}

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host=Config.HOST, 
        port=Config.PORT, 
        reload=True
    )