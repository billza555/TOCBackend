from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import requests
import re
import csv
import uvicorn

app = FastAPI()

BASE_URL = "https://www.musicatm.com"


class Song(BaseModel):
    song: str
    artist: str
    lyrics: str
    chord_image: str


def fetch_page(url: str) -> str:
    res = requests.get(url)
    res.encoding = "utf-8"
    return res.text


def fetch_lyrics_and_chord_image(song_url: str):
    full_url = BASE_URL + song_url
    html = fetch_page(full_url)

    # ดึงเนื้อเพลง
    lyrics_match = re.search(
        r'<div class="lyric-content" id="lyric">.*?<pre[^>]*>(.*?)</pre>',
        html, re.S
    )
    lyrics = ""
    if lyrics_match:
        lyrics = lyrics_match.group(1)
        lyrics = re.sub(r'<br\s*/?>', '\n', lyrics)
        lyrics = re.sub(r'&nbsp;', ' ', lyrics)
        lyrics = re.sub(r'<[^>]+>', '', lyrics)
        lyrics = lyrics.strip()

    # ดึงลิงก์คอร์ด
    chord_match = re.search(
        r'<a class="btn btn-block btn-success" href="([^"]+)">',
        html
    )
    chord_url = BASE_URL + chord_match.group(1) if chord_match else ""

    # ดึงรูปคอร์ดจากหน้า chord
    chord_image_url = ""
    if chord_url:
        chord_html = fetch_page(chord_url)
        img_match = re.search(
            r'<div class="chord-guitar-img">.*?<img[^>]+src="([^"]+)"',
            chord_html, re.S
        )
        if img_match:
            chord_image_url = BASE_URL + img_match.group(1)

    return lyrics, chord_image_url


def extract_songs(html: str):
    """ดึงชื่อเพลง + ศิลปิน + ลิงก์เพลงจากหน้า listing"""
    pattern = r'<a href="([^"]+)" class="list-group-item">.*?<h3>([^<]+) - ([^<]+)</h3>'
    return re.findall(pattern, html, re.S)


@app.get("/songs")
def get_songs(pages: int = 3):
    songs_list = []
    for i in range(1, pages + 1):
        html = fetch_page(BASE_URL + f"/lyric/page{i}")
        results = extract_songs(html)
        for link, song_name, artist in results:
            lyrics, chord_image = fetch_lyrics_and_chord_image(link)
            song = Song(
                song=song_name,
                artist=artist,
                lyrics=lyrics,
                chord_image=chord_image
            )
            songs_list.append(song)
    return JSONResponse(content={"count": len(songs_list), "songs": [s.dict() for s in songs_list]})


@app.get("/songs/csv")
def download_csv(pages: int = 3):
    songs_list = []
    for i in range(1, pages + 1):
        html = fetch_page(BASE_URL + f"/lyric/page{i}")
        results = extract_songs(html)
        for link, song_name, artist in results:
            lyrics, chord_image = fetch_lyrics_and_chord_image(link)
            song = Song(
                song=song_name,
                artist=artist,
                lyrics=lyrics,
                chord_image=chord_image
            )
            songs_list.append(song)

    filename = "songs.csv"
    with open(filename, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(["Song", "Artist", "Lyrics", "Chord Image URL"])
        for s in songs_list:
            writer.writerow([s.song, s.artist, s.lyrics, s.chord_image])


    return FileResponse(filename, media_type="text/csv", filename=filename)


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
