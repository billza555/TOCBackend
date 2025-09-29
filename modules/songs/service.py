import asyncio
import aiohttp
from typing import List, Tuple
from core.config import Config
from core.patterns import (
    LYRICS_PATTERN, BR_PATTERN, NBSP_PATTERN, TAG_PATTERN,
    CHORD_BUTTON_PATTERN, CHORD_IMG_PATTERN, SECTION_PATTERN,
    COMMENT_SPLIT_PATTERN, A_TAG_PATTERN, HREF_PATTERN,
    H3_PATTERN, H3_HEADER_PATTERN, WHITESPACE_PATTERN, 
    HITSONG_SECTION_PATTERN, VIEW_PATTERN, AVATAR_PATTERN
)
from .models import Song

class AsyncSongService:
    def __init__(self):
        self._songs_cache: List[Song] = []
        self._singers: set[str] = set()
        self._session: aiohttp.ClientSession = None
    
    async def __aenter__(self):
        # Initialize session on context entry
        await self._init_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
    
    async def fetch_page(self, url: str, max_retries: int = 2) -> str:
        """Async fetch page content with session validation, URL encoding, and retry logic"""
        
        for attempt in range(max_retries + 1):  # 0, 1, 2 (3 total attempts)
            try:
                # Ensure session exists
                if not self._session or self._session.closed:
                    print(f"Session not available for {url}, reinitializing...")
                    await self._init_session()
                
                # Handle Thai/Unicode URLs properly
                from urllib.parse import quote, unquote
                
                # If URL contains Thai characters, encode them properly
                if any(ord(char) > 127 for char in url):
                    # Split URL to encode only the path part
                    from urllib.parse import urlparse, urlunparse
                    parsed = urlparse(url)
                    # Encode the path while preserving other parts
                    encoded_path = quote(parsed.path.encode('utf-8'), safe='/-.')
                    url = urlunparse((
                        parsed.scheme,
                        parsed.netloc,
                        encoded_path,
                        parsed.params,
                        parsed.query,
                        parsed.fragment
                    ))
                
                async with self._session.get(url) as response:
                    # Handle different response status codes
                    if response.status == 404:
                        print(f"Page not found (404): {url}")
                        return ""
                    elif response.status == 403:
                        print(f"Access forbidden (403): {url}")
                        return ""
                    elif response.status == 500:
                        print(f"Server error (500): {url}")
                        return ""
                    
                    response.raise_for_status()
                    
                    # Try different encoding methods
                    try:
                        # First try UTF-8
                        return await response.text(encoding='utf-8')
                    except UnicodeDecodeError:
                        # Fallback to auto-detection
                        text = await response.text()
                        return text
                        
            except asyncio.TimeoutError:
                if attempt < max_retries:
                    if attempt == 0:
                        # First retry: instant
                        print(f"Timeout fetching {url} (attempt {attempt + 1}/{max_retries + 1}), retrying instantly...")
                    else:
                        # Subsequent retries: progressive backoff
                        wait_time = attempt * 2  # 0s, 2s, 4s...
                        print(f"Timeout fetching {url} (attempt {attempt + 1}/{max_retries + 1}), retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    continue
                else:
                    print(f"Final timeout fetching {url} after {max_retries + 1} attempts")
                    return ""
            except aiohttp.ClientError as e:
                if attempt < max_retries:
                    if attempt == 0:
                        # First retry: instant
                        print(f"Client error fetching {url} (attempt {attempt + 1}/{max_retries + 1}): {e}, retrying instantly...")
                    else:
                        # Subsequent retries: progressive backoff
                        wait_time = attempt * 2  # 0s, 2s, 4s...
                        print(f"Client error fetching {url} (attempt {attempt + 1}/{max_retries + 1}): {e}, retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    continue
                else:
                    print(f"Final client error fetching {url} after {max_retries + 1} attempts: {e}")
                    return ""
            except Exception as e:
                if attempt < max_retries:
                    if attempt == 0:
                        # First retry: instant
                        print(f"Unexpected error fetching {url} (attempt {attempt + 1}/{max_retries + 1}): {type(e).__name__}: {e}, retrying instantly...")
                    else:
                        # Subsequent retries: progressive backoff
                        wait_time = attempt * 2  # 0s, 2s, 4s...
                        print(f"Unexpected error fetching {url} (attempt {attempt + 1}/{max_retries + 1}): {type(e).__name__}: {e}, retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    continue
                else:
                    print(f"Final unexpected error fetching {url} after {max_retries + 1} attempts: {type(e).__name__}: {e}")
                    return ""
        
        return ""  # Should never reach here, but just in case
    
    async def _init_session(self):
        """Initialize session if not exists"""
        if not self._session or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=20,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=45,  # Keep connections alive
                enable_cleanup_closed=True,
                # Remove force_close=True as it conflicts with keepalive_timeout
                ssl=False  # Disable SSL verification if needed
            )
            
            timeout = aiohttp.ClientTimeout(
                total=Config.REQUEST_TIMEOUT if hasattr(Config, 'REQUEST_TIMEOUT') else 30,
                connect=15,  # Connection timeout
                sock_read=30  # Socket read timeout
            )
            
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': getattr(Config, 'USER_AGENT', 'Mozilla/5.0 (compatible; AsyncScraper/1.0)'),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'th,en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
            )
    
    async def fetch_lyrics(self, song_url: str, request_semaphore: asyncio.Semaphore = None, max_retries: int = 2) -> Tuple[str, int, str, str]:
        """Extract lyrics and chord image URL from song page - with optional semaphore control and retry logic"""
        
        async def controlled_fetch(url, retries=max_retries):
            if request_semaphore:
                async with request_semaphore:
                    return await self.fetch_page(url, retries)
            return await self.fetch_page(url, retries)
        
        # Clean and validate the song URL
        if not song_url or not song_url.strip():
            return "", 0, "", ""
            
        # Handle relative URLs
        if song_url.startswith('/'):
            full_url = Config.BASE_URL + song_url
        elif song_url.startswith('http'):
            full_url = song_url
        else:
            full_url = Config.BASE_URL + '/' + song_url
            
        html = await controlled_fetch(full_url, max_retries)
        
        if not html:
            return "", 0, "", ""

        views = 0
        view_match = VIEW_PATTERN.search(html)
        if view_match:
            try:
                views = int(view_match.group(1))
            except (ValueError, TypeError):
                views = 0

        song_transcriber = "" 
        song_transcriber_match = AVATAR_PATTERN.search(html)
        if song_transcriber_match:
            song_transcriber = Config.BASE_URL + song_transcriber_match.group(1)

        # Extract lyrics using pre-compiled patterns
        lyrics_match = LYRICS_PATTERN.search(html)
        lyrics = ""
        if lyrics_match:
            lyrics = lyrics_match.group(1)
            lyrics = BR_PATTERN.sub('\n', lyrics)
            lyrics = NBSP_PATTERN.sub(' ', lyrics)
            lyrics = TAG_PATTERN.sub('', lyrics).strip()
        
        # Extract chord image URL with additional request control and retry
        chord_image_url = ""
        chord_match = CHORD_BUTTON_PATTERN.search(html)
        if chord_match:
            chord_url = Config.BASE_URL + chord_match.group(1)
            chord_html = await controlled_fetch(chord_url, max_retries)
            if chord_html:
                img_match = CHORD_IMG_PATTERN.search(chord_html)
                if img_match:
                    chord_image_url = Config.BASE_URL + img_match.group(1)
        
        return lyrics, views, chord_image_url, song_transcriber
    
    def extract_songs(self, html: str, popular: bool = False) -> List[Tuple[str, str, str]]:
        """Extract song data from page HTML (kept synchronous as it's CPU-bound)"""
        section_match = SECTION_PATTERN.search(html)
        if not section_match:
            return []
        
        section_html = section_match.group(1)
        a_tags = None
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
            href = href_match.group(1) if href_match else ''
            
            h3_match = H3_PATTERN.search(a_tag) or H3_HEADER_PATTERN.search(a_tag)
            if h3_match:
                h3_text = WHITESPACE_PATTERN.sub(' ', h3_match.group(1)).strip()
                if ' - ' in h3_text:
                    song_name, singer_name = h3_text.split(' - ', 1)
                else:
                    song_name, singer_name = h3_text, ''
                songs.append((href, song_name.strip(), singer_name.strip()))
                self._singers.add(singer_name.strip())
        return songs
    
    async def process_song_data(self, song_data: Tuple[str, str, str], request_semaphore: asyncio.Semaphore = None, max_retries: int = 2) -> Song:
        """Process a single song's data - async version with semaphore support and retry logic"""
        link, song_name, singer_name = song_data
        
        # Retry logic for the entire song processing
        for attempt in range(max_retries + 1):
            try:
                lyrics, views, chord_image, song_transcriber = await self.fetch_lyrics(link, request_semaphore, max_retries)
                return Song(
                    song=song_name, 
                    singer=singer_name, 
                    lyrics=lyrics, 
                    chord_image=chord_image, 
                    views=views,
                    song_transcriber=song_transcriber
                )
            except asyncio.TimeoutError:
                if attempt < max_retries:
                    if attempt == 0:
                        # First retry: instant
                        print(f"Timeout processing song '{song_name}' (attempt {attempt + 1}/{max_retries + 1}), retrying instantly...")
                    else:
                        # Subsequent retries: progressive backoff
                        wait_time = attempt * 3  # 0s, 3s, 6s...
                        print(f"Timeout processing song '{song_name}' (attempt {attempt + 1}/{max_retries + 1}), retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    continue
                else:
                    print(f"Final timeout processing song '{song_name}' after {max_retries + 1} attempts")
                    # Return song with empty data rather than None
                    return Song(
                        song=song_name, 
                        singer=singer_name, 
                        lyrics="", 
                        chord_image="", 
                        views=0,
                        song_transcriber=""
                    )
            except Exception as e:
                if attempt < max_retries:
                    if attempt == 0:
                        # First retry: instant
                        print(f"Error processing song '{song_name}' (attempt {attempt + 1}/{max_retries + 1}): {e}, retrying instantly...")
                    else:
                        # Subsequent retries: progressive backoff
                        wait_time = attempt * 3  # 0s, 3s, 6s...
                        print(f"Error processing song '{song_name}' (attempt {attempt + 1}/{max_retries + 1}): {e}, retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    continue
                else:
                    print(f"Final error processing song '{song_name}' after {max_retries + 1} attempts: {e}")
                    # Return song with empty data rather than None
                    return Song(
                        song=song_name, 
                        singer=singer_name, 
                        lyrics="", 
                        chord_image="", 
                        views=0,
                        song_transcriber=""
                    )
    
    async def get_songs_list(
        self,
        page: int = 1, 
        page_concurrency: int = 10,  # Concurrent page fetches
        song_concurrency: int = 100,  # Concurrent song processing
        popular: bool = False,
        max_retries: int = 2  # Maximum retries for failed operations
    ) -> List[Song]:
        """Get list of songs with dual-level semaphore control and retry logic"""
        all_song_data = []
        
        # Semaphore for page fetching
        page_semaphore = asyncio.Semaphore(page_concurrency)
        
        async def fetch_page_bounded(page_num):
            async with page_semaphore:
                return await self.fetch_page(f"{Config.BASE_URL}/lyric/page{page_num}", max_retries)
        
        # Fetch pages with controlled concurrency
        page_tasks = [fetch_page_bounded(i) for i in range(1, page + 1)]
        pages_html = await asyncio.gather(*page_tasks, return_exceptions=True)
        
        # Extract song data from all pages
        for html in pages_html:
            if isinstance(html, str) and html:
                all_song_data.extend(self.extract_songs(html, popular))
        
        print(f"Found {len(all_song_data)} songs to process")
        
        # Process songs with controlled concurrency
        songs_list = []
        song_semaphore = asyncio.Semaphore(song_concurrency)
        
        async def bounded_song_process(song_data):
            async with song_semaphore:
                try:
                    # Create a request-level semaphore for HTTP calls within each song
                    request_semaphore = asyncio.Semaphore(2)  # Max 2 HTTP requests per song concurrently
                    return await self.process_song_data(song_data, request_semaphore, max_retries)
                except Exception as e:
                    print(f"Unexpected error in bounded_song_process for {song_data[1]}: {e}")
                    # Return song with empty data rather than None
                    return Song(
                        song=song_data[1], 
                        singer=song_data[2], 
                        lyrics="", 
                        chord_image="", 
                        views=0
                    )
        
        # Process songs in batches for better memory management
        batch_size = 250  # Process in batches to avoid memory issues
        
        for i in range(0, len(all_song_data), batch_size):
            batch = all_song_data[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(all_song_data)-1)//batch_size + 1}")
            
            song_tasks = [bounded_song_process(song_data) for song_data in batch]
            batch_results = await asyncio.gather(*song_tasks, return_exceptions=True)
            
            # Filter successful results
            for result in batch_results:
                if isinstance(result, Song):
                    songs_list.append(result)
                elif isinstance(result, Exception):
                    print(f"Exception in batch result: {result}")
                elif result is not None:
                    print(f"Unexpected result type: {type(result)}")
        
        return songs_list
    
    async def initialize(self):
        """Initialize session manually (alternative to context manager)"""
        await self._init_session()
    
    async def close(self):
        """Close session manually"""
        if self._session:
            await self._session.close()
            self._session = None

    async def update_cache(self, max_retries: int = 2):
        """Update cache with all songs - with retry support"""
        # Ensure session is initialized
        if not self._session or self._session.closed:
            await self._init_session()
            
        self._songs_cache.clear()
        self._singers.clear()
        self._songs_cache = await self.get_songs_list(253, max_retries=max_retries)
        return {"message": f"found {len(self._songs_cache)} songs"}
    
    def get_singers(self) -> set[str]:
        return set(self._singers)
    
    def get_songs(self) -> List[Song]:
        return list(self._songs_cache)