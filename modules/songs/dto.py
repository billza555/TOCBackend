from pydantic import BaseModel
from typing import List, Optional
from .models import Song

class SongListResponse(BaseModel):
    count: int
    songs: List[Song]
    is_next: bool

class SongQueryParams(BaseModel):
    page: Optional[int] = 1
    song: Optional[str] = None
    singer: Optional[str] = None
    lyric: Optional[str] = None

class SingerListResponse(BaseModel):
    count: int
    singers: List[str]
    is_next: bool