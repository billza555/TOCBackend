from pydantic import BaseModel
from typing import List, Optional
from .models import Song

class SongListResponse(BaseModel):
    count: int
    songs: List[Song]

class SongQueryParams(BaseModel):
    page: Optional[int] = 1
    song: Optional[str] = None
    artist: Optional[str] = None
    lyric: Optional[str] = None