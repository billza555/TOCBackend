from typing import List, Tuple
from core.config import Config
from core.patterns import (
    LYRICS_PATTERN, BR_PATTERN, NBSP_PATTERN, TAG_PATTERN,
    CHORD_BUTTON_PATTERN, CHORD_IMG_PATTERN, SECTION_PATTERN,
    COMMENT_SPLIT_PATTERN, A_TAG_PATTERN, HREF_PATTERN,
    H3_PATTERN, H3_HEADER_PATTERN, WHITESPACE_PATTERN, HITSONG_SECTION_PATTERN, VIEW_PATTERN
)
from shared.http_client import fetch
from .models import Song
import asyncio
import aiohttp

CONCURRENT_SONGS = 50 

semaphore = asyncio.Semaphore(CONCURRENT_SONGS)

class SongService:
    def __init__(self):
        self._songs_cache: List[Song] = []
        self._singers: set[str] = set()
    
    @staticmethod
    async def extract_lyrics_and_chord_image(session: aiohttp.ClientSession, song_url: str) -> Tuple[str, int, str]:
        full_url = Config.BASE_URL + song_url
        html = await fetch(session, full_url)

        # Views
        views = 0
        view_match = VIEW_PATTERN.search(html)
        if view_match:
            views = int(view_match.group(1))

        # Lyrics
        lyrics = ""
        lyrics_match = LYRICS_PATTERN.search(html)
        if lyrics_match:
            lyrics = lyrics_match.group(1)
            lyrics = BR_PATTERN.sub("\n", lyrics)
            lyrics = NBSP_PATTERN.sub(" ", lyrics)
            lyrics = TAG_PATTERN.sub("", lyrics).strip()

        # Chord image
        chord_image_url = ""
        chord_match = CHORD_BUTTON_PATTERN.search(html)
        if chord_match:
            chord_url = Config.BASE_URL + chord_match.group(1)
            chord_html = await fetch(session, chord_url)
            img_match = CHORD_IMG_PATTERN.search(chord_html)
            if img_match:
                chord_image_url = Config.BASE_URL + img_match.group(1)

        return lyrics, views, chord_image_url
    
    async def extract_songs(self, html: str, popular: bool = False) -> List[Tuple[str, str, str]]:
        section_match = SECTION_PATTERN.search(html)
        if not section_match:
            return []

        section_html = section_match.group(1)
        if popular:
            section_b = COMMENT_SPLIT_PATTERN.split(section_html, maxsplit=1)[1]
            hit_section_match = HITSONG_SECTION_PATTERN.search(section_b)
            if not hit_section_match:
                return []
            hit_section_html = hit_section_match.group(1)
            a_tags = A_TAG_PATTERN.findall(hit_section_html)
        else:
            section_hit_update = COMMENT_SPLIT_PATTERN.split(section_html, maxsplit=1)[0]
            a_tags = A_TAG_PATTERN.findall(section_hit_update)

        songs = []
        for a_tag in a_tags:
            href_match = HREF_PATTERN.search(a_tag)
            href = href_match.group(1) if href_match else ""

            h3_match = H3_PATTERN.search(a_tag) or H3_HEADER_PATTERN.search(a_tag)
            if h3_match:
                h3_text = WHITESPACE_PATTERN.sub(" ", h3_match.group(1)).strip()
                if " - " in h3_text:
                    song_name, singer_name = h3_text.split(" - ", 1)
                else:
                    song_name, singer_name = h3_text, ""
                songs.append((href, song_name.strip(), singer_name.strip()))
                self._singers.add(singer_name.strip())
        return songs

    async def fetch_song_data(self, session: aiohttp.ClientSession, song_data: Tuple[str, str, str]) -> Song:
        async with semaphore:
            link, song_name, singer_name = song_data
            try:
                lyrics, views, chord_image = await self.extract_lyrics_and_chord_image(session, link)
                print(f"Fetched : {song_name} by {singer_name} with {views} views")
                return Song(song=song_name, singer=singer_name, lyrics=lyrics, chord_image=chord_image, views=views)
            except Exception as e:
                print(f"Error fetching song {song_name}: {e}")
                return Song(song=song_name, singer=singer_name, lyrics="", chord_image="", views=0)
    
    async def get_songs_list(
    self,
    page: int = 1, 
) -> List[Song]:
        pages = range(1, page + 1)  # all lyric pages
    
        async with aiohttp.ClientSession() as session:
            # Fetch all lyric pages concurrently
            page_tasks = [asyncio.create_task(fetch(session, f"{Config.BASE_URL}/lyric/page{p}")) for p in pages]
            page_htmls = await asyncio.gather(*page_tasks)
    
        # Extract songs from all pages
            all_song_links: List[Tuple[str, str, str]] = []
            for html in page_htmls:
                songs_on_page = await self.extract_songs(html)
                all_song_links.extend(songs_on_page)

        # Fetch each song's lyrics & chord concurrently - session is still open here
            song_tasks = [asyncio.create_task(self.fetch_song_data(session, s)) for s in all_song_links]
            songs: List[Song] = await asyncio.gather(*song_tasks)

        self._songs_cache.extend(songs)
        return songs  # Added return statement
    
    async def update_cache(self):
        self._songs_cache.clear()
        self._singers.clear()
        await self.get_songs_list(253)
        return {"message" : f"found {len(self._songs_cache)} songs"}

    def get_singers(self) -> set[str]:
        return set(self._singers)
    
    def get_songs(self) -> List[Song]:
        return list(self._songs_cache)