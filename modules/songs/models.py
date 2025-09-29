from pydantic import BaseModel

class Song(BaseModel):
    song: str
    singer: str
    lyrics: str
    chord_image: str
    views: int
    song_transcriber: str