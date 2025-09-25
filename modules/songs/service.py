from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor
from core.config import Config
from core.patterns import (
    LYRICS_PATTERN, BR_PATTERN, NBSP_PATTERN, TAG_PATTERN,
    CHORD_BUTTON_PATTERN, CHORD_IMG_PATTERN, SECTION_PATTERN,
    COMMENT_SPLIT_PATTERN, A_TAG_PATTERN, HREF_PATTERN,
    H3_PATTERN, H3_HEADER_PATTERN, WHITESPACE_PATTERN
)
from shared.http_client import fetch_page
from .models import Song

class SongService:
    
    @staticmethod
    def fetch_lyrics_and_chord_image(song_url: str) -> Tuple[str, str]:
        """Extract lyrics and chord image URL from song page"""
        full_url = Config.BASE_URL + song_url
        html = fetch_page(full_url)
        
        # Extract lyrics using pre-compiled patterns
        lyrics_match = LYRICS_PATTERN.search(html)
        lyrics = ""
        if lyrics_match:
            lyrics = lyrics_match.group(1)
            lyrics = BR_PATTERN.sub('\n', lyrics)
            lyrics = NBSP_PATTERN.sub(' ', lyrics)
            lyrics = TAG_PATTERN.sub('', lyrics).strip()
        
        # Extract chord image URL
        chord_image_url = ""
        chord_match = CHORD_BUTTON_PATTERN.search(html)
        if chord_match:
            chord_url = Config.BASE_URL + chord_match.group(1)
            chord_html = fetch_page(chord_url)
            img_match = CHORD_IMG_PATTERN.search(chord_html)
            if img_match:
                chord_image_url = Config.BASE_URL + img_match.group(1)
        
        return lyrics, chord_image_url
    
    @staticmethod
    def extract_songs(html: str) -> List[Tuple[str, str, str]]:
        """Extract song data from page HTML"""
        section_match = SECTION_PATTERN.search(html)
        if not section_match:
            return []
        
        section_html = section_match.group(1)
        section_hit = COMMENT_SPLIT_PATTERN.split(section_html, maxsplit=1)[0]
        a_tags = A_TAG_PATTERN.findall(section_hit)
        
        songs = []
        for a_tag in a_tags:
            href_match = HREF_PATTERN.search(a_tag)
            href = href_match.group(1) if href_match else ''
            
            h3_match = H3_PATTERN.search(a_tag) or H3_HEADER_PATTERN.search(a_tag)
            if h3_match:
                h3_text = WHITESPACE_PATTERN.sub(' ', h3_match.group(1)).strip()
                if ' - ' in h3_text:
                    song_name, artist_name = h3_text.split(' - ', 1)
                else:
                    song_name, artist_name = h3_text, ''
                songs.append((href, song_name.strip(), artist_name.strip()))
        
        return songs
    
    @staticmethod
    def process_song_data(song_data: Tuple[str, str, str]) -> Song:
        """Process a single song's data - designed for multithreading"""
        link, song_name, artist_name = song_data
        lyrics, chord_image = SongService.fetch_lyrics_and_chord_image(link)
        return Song(song=song_name, artist=artist_name, lyrics=lyrics, chord_image=chord_image)
    
    @staticmethod
    def get_songs_list(
        page: int = 1, 
        song: str = None, 
        artist: str = None, 
        lyric: str = None, 
        max_workers: int = Config.MAX_WORKERS
    ) -> List[Song]:
        """Get list of songs with optional filters and multithreading"""
        all_song_data = []
        
        # Collect all song data first
        for i in range(1, page + 1):
            html = fetch_page(f"{Config.BASE_URL}/lyric/page{i}")
            all_song_data.extend(SongService.extract_songs(html))
        
        # Process songs in parallel
        songs_list = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_song = {
                executor.submit(SongService.process_song_data, song_data): song_data 
                for song_data in all_song_data
            }
            
            # Collect results
            for future in future_to_song:
                try:
                    song_obj = future.result(timeout=Config.SONG_PROCESSING_TIMEOUT)
                    songs_list.append(song_obj)
                except Exception as e:
                    print(f"Error processing song: {e}")
                    continue
        
        # Apply filters
        if song:
            song_lower = song.lower()
            songs_list = [s for s in songs_list if song_lower in s.song.lower()]
        if artist:
            artist_lower = artist.lower()
            songs_list = [s for s in songs_list if artist_lower in s.artist.lower()]
        if lyric:
            lyric_lower = lyric.lower()
            songs_list = [s for s in songs_list if lyric_lower in s.lyrics.lower()]
        
        return songs_list