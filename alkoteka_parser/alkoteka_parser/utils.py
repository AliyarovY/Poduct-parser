import requests
import logging
from bs4 import BeautifulSoup
from typing import List
import time

logger = logging.getLogger(__name__)


def fetch_free_proxies(source: str = 'free-proxy-list') -> List[str]:
    """
    Fetch free proxies from various sources.

    Sources:
    - 'free-proxy-list': https://free-proxy-list.net/
    - 'sslproxies': https://www.sslproxies.org/
    - 'us-proxy': https://www.us-proxy.org/
    """

    urls = {
        'free-proxy-list': 'https://free-proxy-list.net/',
        'sslproxies': 'https://www.sslproxies.org/',
        'us-proxy': 'https://www.us-proxy.org/',
    }

    if source not in urls:
        logger.error(f"Unknown source: {source}")
        return []

    url = urls[source]
    proxies = []

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', {'class': 'table'})

        if not table:
            logger.warning(f"Proxy table not found on {source}")
            return []

        rows = table.find_all('tr')[1:]

        for row in rows[:20]:
            cols = row.find_all('td')
            if len(cols) >= 2:
                ip = cols[0].text.strip()
                port = cols[1].text.strip()
                proxy = f"http://{ip}:{port}"
                proxies.append(proxy)

        logger.info(f"Fetched {len(proxies)} proxies from {source}")
        return proxies

    except requests.RequestException as e:
        logger.error(f"Error fetching proxies from {source}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return []


def validate_proxy(proxy: str, timeout: float = 5.0) -> bool:
    """
    Quick validation of proxy by making a test request.

    Args:
        proxy: Proxy URL (e.g., 'http://ip:port')
        timeout: Request timeout in seconds

    Returns:
        True if proxy is working, False otherwise
    """

    test_urls = [
        'http://httpbin.org/ip',
        'http://example.com',
    ]

    for test_url in test_urls:
        try:
            response = requests.get(
                test_url,
                proxies={'http': proxy, 'https': proxy},
                timeout=timeout
            )
            if response.status_code == 200:
                logger.debug(f"Proxy {proxy} validated successfully")
                return True
        except:
            continue

    logger.warning(f"Proxy {proxy} validation failed")
    return False


def save_proxies_to_file(proxies: List[str], filename: str = 'proxies.txt') -> int:
    """
    Save proxies to file.

    Args:
        proxies: List of proxy URLs
        filename: Output filename

    Returns:
        Number of proxies saved
    """

    try:
        with open(filename, 'w') as f:
            for proxy in proxies:
                f.write(f"{proxy}\n")

        logger.info(f"Saved {len(proxies)} proxies to {filename}")
        return len(proxies)

    except Exception as e:
        logger.error(f"Error saving proxies: {e}")
        return 0


def get_free_proxies_and_validate(source: str = 'free-proxy-list',
                                   validate: bool = True,
                                   save_file: bool = True) -> List[str]:
    """
    Fetch, optionally validate, and optionally save proxies.

    Args:
        source: Proxy source name
        validate: Whether to validate proxies
        save_file: Whether to save to proxies.txt

    Returns:
        List of validated proxies
    """

    logger.info(f"Fetching proxies from {source}...")
    proxies = fetch_free_proxies(source)

    if not proxies:
        logger.error("No proxies found")
        return []

    logger.info(f"Found {len(proxies)} proxies")

    if validate:
        logger.info("Validating proxies (this may take a while)...")
        validated = []

        for i, proxy in enumerate(proxies):
            if validate_proxy(proxy):
                validated.append(proxy)
            if (i + 1) % 10 == 0:
                logger.info(f"Validated {i + 1}/{len(proxies)} proxies")
            time.sleep(0.5)

        logger.info(f"Validation complete: {len(validated)} working proxies")
        proxies = validated

    if save_file and proxies:
        save_proxies_to_file(proxies)

    return proxies
