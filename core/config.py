class Config:
    # API Configuration
    BASE_URL = "https://www.musicatm.com"
    HOST = "127.0.0.1"
    PORT = 8000
    
    # Threading Configuration
    MAX_WORKERS = 5
    REQUEST_TIMEOUT = 10
    SONG_PROCESSING_TIMEOUT = 60
    
    # HTTP Configuration
    USER_AGENT = "Mozilla/5.0 (compatible; MusicScraper/1.0)"