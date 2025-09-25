import re
import csv
import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
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
    lyrics_match = re.search(r'<div class="lyric-content" id="lyric">.*?<pre[^>]*>(.*?)</pre>', html, re.S)
    lyrics = ""
    if lyrics_match:
        lyrics = lyrics_match.group(1)
        lyrics = re.sub(r'<br\s*/?>', '\n', lyrics)
        lyrics = re.sub(r'&nbsp;', ' ', lyrics)
        lyrics = re.sub(r'<[^>]+>', '', lyrics).strip()
    chord_image_url = ""
    chord_match = re.search(r'<a class="btn btn-block btn-success" href="([^"]+)">', html)
    if chord_match:
        chord_url = BASE_URL + chord_match.group(1)
        chord_html = fetch_page(chord_url)
        img_match = re.search(r'<div class="chord-guitar-img">.*?<img[^>]+src="([^"]+)"', chord_html, re.S)
        if img_match:
            chord_image_url = BASE_URL + img_match.group(1)
    return lyrics, chord_image_url

def extract_songs(html: str):
    section_match = re.search(
        r'<h2 class="panel-title"[^>]*>.*?เนื้อเพลงฮิตเพิ่มล่าสุด.*?</h2>.*?<div class="list-group main_list">(.*)</div>',
        html, re.S
    )
    if not section_match:
        return []
    section_html = section_match.group(1)
    section_hit = re.split(r'<div class="panel panel-info"[^>]*id="comment_lyric_list">', section_html, flags=re.S)[0]
    a_tags = re.findall(r'<a [^>]*>.*?</a>', section_hit, re.S)
    songs = []
    for a_tag in a_tags:
        href_match = re.search(r'href="([^"]+)"', a_tag)
        href = href_match.group(1) if href_match else ''
        h3_match = re.search(r'<h3>(.*?)</h3>', a_tag, re.S) or re.search(r'<h3>(.*?)</header>', a_tag, re.S)
        if h3_match:
            h3_text = re.sub(r'\s+', ' ', h3_match.group(1)).strip()
            if ' - ' in h3_text:
                song_name, artist_name = h3_text.split(' - ', 1)
            else:
                song_name, artist_name = h3_text, ''
            songs.append((href, song_name.strip(), artist_name.strip()))
    return songs

def get_songs_list(page: int = 1, song: str = None, artist: str = None, lyric: str = None):
    songs_list = []
    for i in range(1, page + 1):
        html = fetch_page(f"{BASE_URL}/lyric/page{i}")
        for link, song_name, artist_name in extract_songs(html):
            lyrics, chord_image = fetch_lyrics_and_chord_image(link)
            songs_list.append(Song(song=song_name, artist=artist_name, lyrics=lyrics, chord_image=chord_image))
    if song:
        songs_list = [s for s in songs_list if song.lower() in s.song.lower()]
    if artist:
        songs_list = [s for s in songs_list if artist.lower() in s.artist.lower()]
    if lyric:
        songs_list = [s for s in songs_list if lyric.lower() in s.lyrics.lower()]
    return songs_list

@app.get("/songs")
def get_songs(page: int = 1, song: str = None, artist: str = None, lyric: str = None):
    songs_list = get_songs_list(page, song, artist, lyric)
    return JSONResponse(content={"count": len(songs_list), "songs": [s.dict() for s in songs_list]})

@app.get("/songs/csv")
def download_csv(page: int = 1, song: str = None, artist: str = None, lyric: str = None):
    songs_list = get_songs_list(page, song, artist, lyric)
    filename = "songs.csv"
    with open(filename, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(["Song", "Artist", "Lyrics", "Chord Image URL"])
        for s in songs_list:
            writer.writerow([s.song, s.artist, s.lyrics, s.chord_image])
    return FileResponse(filename, media_type="text/csv", filename=filename)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)