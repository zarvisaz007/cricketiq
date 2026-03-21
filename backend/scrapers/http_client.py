"""
scrapers/http_client.py
HTTP client with rotating user-agents, rate limiting, and exponential backoff.
Ported from Claude-cricket, adapted for CricketIQ.
"""
import time
import hashlib
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Rotating user agents — deterministic per URL
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:119.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 OPR/105.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Vivaldi/6.4",
]

RATE_LIMIT_DELAY = 2.0  # seconds between requests
MAX_RETRIES = 5
_last_request_time = 0.0
_session = None


def _get_ua(url: str) -> str:
    """Deterministic user-agent selection based on URL hash."""
    idx = int(hashlib.md5(url.encode()).hexdigest(), 16) % len(USER_AGENTS)
    return USER_AGENTS[idx]


def _get_session() -> requests.Session:
    """Get or create a reusable session with retry adapter."""
    global _session
    if _session is None:
        _session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        _session.mount("http://", adapter)
        _session.mount("https://", adapter)
    return _session


def scrape_delay():
    """Enforce minimum delay between requests."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY - elapsed)
    _last_request_time = time.time()


def get_page(url: str, params: dict = None, timeout: int = 30) -> requests.Response:
    """
    Fetch a URL with rate limiting, rotating UA, and retry logic.
    Raises on final failure after retries.
    """
    session = _get_session()
    headers = {
        "User-Agent": _get_ua(url),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
    }

    last_error = None
    for attempt in range(MAX_RETRIES):
        scrape_delay()
        try:
            resp = session.get(url, params=params, headers=headers, timeout=timeout)
            if resp.status_code == 429:
                wait = min(2 ** attempt * 2, 30)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                wait = min(2 ** attempt, 30)
                time.sleep(wait)

    raise last_error or Exception(f"Failed to fetch {url} after {MAX_RETRIES} attempts")


def get_json(url: str, params: dict = None, timeout: int = 30) -> dict:
    """Fetch URL and parse as JSON."""
    resp = get_page(url, params=params, timeout=timeout)
    return resp.json()


def reset_session():
    """Reset the HTTP session (e.g., after errors)."""
    global _session
    if _session:
        _session.close()
    _session = None
