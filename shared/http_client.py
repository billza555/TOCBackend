import requests
import threading
from core.config import Config

# Thread-local storage for requests sessions
thread_local = threading.local()

def get_session():
    """Get thread-local requests session for connection reuse"""
    if not hasattr(thread_local, "session"):
        thread_local.session = requests.Session()
        # Configure session for better performance
        thread_local.session.headers.update({
            'User-Agent': Config.USER_AGENT
        })
    return thread_local.session

def fetch_page(url: str) -> str:
    """Fetch page content from URL"""
    session = get_session()
    res = session.get(url, timeout=Config.REQUEST_TIMEOUT)
    res.encoding = "utf-8"
    return res.text