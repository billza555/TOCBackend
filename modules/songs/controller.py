import csv
from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from typing import Optional
from .service import SongService
from .dto import SongListResponse, SingerListResponse

# Create router for song endpoints
router = APIRouter(prefix="/songs", tags=["songs"])

song_service = SongService()

def apply_filters(songs, song=None, singer=None, lyric=None):
    if song:
        songs = [s for s in songs if song.lower() in s.song.lower()]
    if singer:
        songs = [s for s in songs if singer.lower() in s.singer.lower()]
    if lyric:
        songs = [s for s in songs if lyric.lower() in s.lyrics.lower()]
    return songs

def paginate(items: list, page: int, page_size: int):
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end]

@router.get("/crawler")
def crawl_new_songs():
    return song_service.update_cache()

@router.get("/singer")
def get_singers(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),):
    singers = list(song_service.get_singers())
    singers_page = paginate(singers, page, page_size)
    is_next = (page * page_size) < len(singers)
    return SingerListResponse(
        count=len(singers_page),
        singers=singers_page,
        is_next=is_next
    )

@router.get("", response_model=SongListResponse)
def get_songs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    song: Optional[str] = Query(None, description="Filter by song name"),
    singer: Optional[str] = Query(None, description="Filter by singer name"),
    lyric: Optional[str] = Query(None, description="Filter by lyrics content")
):
    """Get list of songs with optional filters and pagination"""
    songs_list = song_service.get_songs()
    songs_list = apply_filters(songs_list, song, singer, lyric)

    total = len(songs_list)
    songs_page = paginate(songs_list, page, page_size)

    # มีหน้าถัดไปหรือไม่
    is_next = (page * page_size) < total

    return SongListResponse(
        count=len(songs_page),
        songs=songs_page,
        is_next=is_next
    )

@router.get("/csv")
def download_csv(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    song: Optional[str] = Query(None, description="Filter by song name"),
    singer: Optional[str] = Query(None, description="Filter by singer name"),
    lyric: Optional[str] = Query(None, description="Filter by lyrics content")
):
    """Download songs as CSV file"""
    songs_list = song_service.get_songs()
    songs_list = apply_filters(songs_list, song, singer, lyric)
    songs_page = paginate(songs_list, page, page_size)
    
    filename = "songs.csv"
    with open(filename, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(["Song", "Singer", "Lyrics", "Chord Image URL"])
        for s in songs_page:
            writer.writerow([s.song, s.singer, s.lyrics, s.chord_image])
    
    return FileResponse(filename, media_type="text/csv", filename=filename)