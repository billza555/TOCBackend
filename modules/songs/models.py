from pydantic import BaseModel

class Song(BaseModel):
    song: str
    artist: str
    lyrics: str
    chord_image: str