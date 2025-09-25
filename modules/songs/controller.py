import csv
from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from typing import Optional
from .service import SongService
from .dto import SongListResponse

# Create router for song endpoints
router = APIRouter(prefix="/songs", tags=["songs"])

@router.get("", response_model=SongListResponse)
def get_songs(
    page: int = Query(1, ge=1, description="Page number"),
    song: Optional[str] = Query(None, description="Filter by song name"),
    artist: Optional[str] = Query(None, description="Filter by artist name"),
    lyric: Optional[str] = Query(None, description="Filter by lyrics content")
):
    """Get list of songs with optional filters"""
    songs_list = SongService.get_songs_list(page, song, artist, lyric)
    return SongListResponse(count=len(songs_list), songs=songs_list)

@router.get("/csv")
def download_csv(
    page: int = Query(1, ge=1, description="Page number"),
    song: Optional[str] = Query(None, description="Filter by song name"),
    artist: Optional[str] = Query(None, description="Filter by artist name"),
    lyric: Optional[str] = Query(None, description="Filter by lyrics content")
):
    """Download songs as CSV file"""
    songs_list = SongService.get_songs_list(page, song, artist, lyric)
    filename = "songs.csv"
    
    with open(filename, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(["Song", "Artist", "Lyrics", "Chord Image URL"])
        for s in songs_list:
            writer.writerow([s.song, s.artist, s.lyrics, s.chord_image])
    
    return FileResponse(filename, media_type="text/csv", filename=filename)