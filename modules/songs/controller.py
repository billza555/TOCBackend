import asyncio
import time
from fastapi import APIRouter, Query, BackgroundTasks
from fastapi.responses import FileResponse
from typing import Optional
from .service import AsyncSongService
from .dto import SongListResponse, SingerListResponse
import csv
import time

router = APIRouter(prefix="/songs", tags=["songs"])
song_service = AsyncSongService()

# request counter (global for now)
REQUEST_COUNTER = 1
CRAWL_THRESHOLD = 1000
LOCK = asyncio.Lock()

async def maybe_trigger_crawl():
    global REQUEST_COUNTER
    async with LOCK:
        if REQUEST_COUNTER % CRAWL_THRESHOLD == 0:
            print("🚀 Threshold reached, refreshing cache...")
            # run in background so requests don't block
            asyncio.create_task(song_service.update_cache())

def apply_filters(songs, song=None, singer=None, lyric=None, min_views=None):
    if song:
        songs = [s for s in songs if song.lower() in s.song.lower()]
    if singer:
        songs = [s for s in songs if singer.lower() in s.singer.lower()]
    if lyric:
        songs = [s for s in songs if lyric.lower() in s.lyrics.lower()]
    if min_views:
        songs = [s for s in songs if getattr(s, "views", 0) >= min_views]
    return songs

def paginate(items: list, page: int, page_size: int):
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end]

@router.get("", response_model=SongListResponse)
async def get_songs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    song: Optional[str] = None,
    singer: Optional[str] = None,
    lyric: Optional[str] = None,
    min_views: Optional[int] = Query(1, ge=1),
    popular: bool = False
):
    global REQUEST_COUNTER
    await maybe_trigger_crawl()
    REQUEST_COUNTER += 1

    songs_list = await song_service.get_songs_list(1, popular=True) if popular else song_service.get_songs()
    songs_list = apply_filters(songs_list, song, singer, lyric, min_views)

    total = len(songs_list)
    songs_page = paginate(songs_list, page, page_size)
    is_next = (page * page_size) < total
    return SongListResponse(count=len(songs_page), songs=songs_page, is_next=is_next)

@router.get("/singer")
async def get_singers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    global REQUEST_COUNTER
    await maybe_trigger_crawl()
    REQUEST_COUNTER += 1

    singers = list(song_service.get_singers())
    singers_page = paginate(singers, page, page_size)
    is_next = (page * page_size) < len(singers)
    return SingerListResponse(count=len(singers_page), singers=singers_page, is_next=is_next)

@router.get("/csv")
async def download_csv(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    song: Optional[str] = None,
    singer: Optional[str] = None,
    lyric: Optional[str] = None,
    min_views: Optional[int] = Query(1, ge=1),
    popular: bool = False
):
    global REQUEST_COUNTER
    await maybe_trigger_crawl()
    REQUEST_COUNTER += 1

    songs_list = song_service.get_songs_list(1, popular=True) if popular else song_service.get_songs()
    songs_list = apply_filters(songs_list, song, singer, lyric, min_views)
    songs_page = paginate(songs_list, page, page_size)
    
    filename = "songs.csv"
    with open(filename, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(["Song", "Singer", "Lyrics", "Chord Image URL", "Views"])
        for s in songs_page:
            writer.writerow([s.song, s.singer, s.lyrics, s.chord_image, getattr(s, "views", 0)])
    
    return FileResponse(filename, media_type="text/csv", filename=filename)

@router.get("/crawler")
async def crawl_new_songs():
    start_time = time.time()
    res = await song_service.update_cache()
    elapsed_time = time.time() - start_time
    print(f"Crawling completed in {elapsed_time:.2f} seconds")
    return res
