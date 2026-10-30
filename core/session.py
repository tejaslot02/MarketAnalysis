"""Robust Session Manager for NSE India with cookie harvesting and anti-bot handling."""

import logging
import random
import time
from typing import Any, Dict, Optional

try:
    from curl_cffi import requests as curl_requests

    HAS_CURL_CFFI = True
except ImportError:
    import requests as curl_requests  # type: ignore

    HAS_CURL_CFFI = False

import requests

from config.settings import NSEConfig, config

logger = logging.getLogger("market_analysis.session")


class NSEException(Exception):
    """Base exception for NSE crawler and session errors."""

    pass


class NSEConnectionError(NSEException):
    """Raised when connection drops, timeouts, or network failures occur."""

    pass


class NSESessionExpiredError(NSEException):
    """Raised when session cookies expire or access is denied (401/403)."""

    pass


class NSERateLimitError(NSEException):
    """Raised when NSE throttles requests with HTTP 429."""

    pass


class NSEDataFormatError(NSEException):
    """Raised when the received payload is empty, invalid, or non-JSON."""

    pass


class NSESessionManager:
    """Manages an authenticated, cookie-warmed session to communicate with NSE India endpoints.

    Visits the base homepage and option chain UI page first to harvest Akamai/Cloudflare
    security cookies (_abck, bm_sz, ak_bmsc, nsit) and realistic browser signatures.
    """

    def __init__(self, cfg: Optional[NSEConfig] = None, use_curl_cffi: bool = True):
        """Initializes the session manager.

        Args:
            cfg: Configuration instance. Defaults to global config.
            use_curl_cffi: If True and curl_cffi is installed, impersonates Chrome TLS fingerprint.
        """
        self.cfg = cfg or config
        self.use_curl_cffi = use_curl_cffi and HAS_CURL_CFFI
        self._session: Optional[Any] = None
        self._last_warmed: float = 0.0
        self._is_warmed: bool = False

    def _create_raw_session(self) -> Any:
        """Instantiates a fresh requests or curl_cffi Session object."""
        if self.use_curl_cffi:
            logger.debug("Creating curl_cffi Session with Chrome 124 TLS impersonation")
            session = curl_requests.Session(impersonate="chrome124")
        else:
            logger.debug("Creating standard requests.Session")
            session = requests.Session()

        # Update initial headers
        session.headers.update(self.cfg.default_headers)
        return session

    def warm_up(self, force: bool = False) -> bool:
        """Visits NSE homepage and Option Chain page to harvest mandatory session cookies.

        Args:
            force: If True, discards existing session and performs a fresh handshake.

        Returns:
            True if session was warmed successfully, False otherwise.
        """
        now = time.time()
        if not force and self._is_warmed and (now - self._last_warmed < self.cfg.session_ttl_seconds):
            logger.debug("Session is already warm and valid (age: %.1fs)", now - self._last_warmed)
            return True

        logger.info("Initializing fresh NSE session and harvesting cookies...")
        if self._session is not None:
            try:
                self._session.close()
            except Exception:
                pass

        self._session = self._create_raw_session()
        self._is_warmed = False

        try:
            # Stage 1: Hit NSE Homepage to acquire primary perimeter cookies
            logger.debug("Visiting base homepage: %s", self.cfg.base_url)
            r1 = self._session.get(
                self.cfg.base_url,
                headers=self.cfg.default_headers,
                timeout=self.cfg.request_timeout,
            )
            logger.debug("Homepage status: %d, Cookies: %s", r1.status_code, list(self.get_cookies().keys()))

            # Polite delay with slight jitter to mimic human navigation
            delay = random.uniform(self.cfg.polite_delay_min, self.cfg.polite_delay_max)
            time.sleep(delay)

            # Stage 2: Hit Option Chain landing page to harvest secondary tracking cookies
            logger.debug("Visiting Option Chain portal: %s", self.cfg.option_chain_page_url)
            r2 = self._session.get(
                self.cfg.option_chain_page_url,
                headers=self.cfg.default_headers,
                timeout=self.cfg.request_timeout,
            )
            logger.debug("Option chain page status: %d, Cookies: %s", r2.status_code, list(self.get_cookies().keys()))

            # Stage 3: Prepare API headers for subsequent JSON requests
            self._session.headers.update(self.cfg.api_headers)

            self._is_warmed = True
            self._last_warmed = time.time()
            logger.info(
                "NSE session successfully warmed up. Active cookies: %s",
                list(self.get_cookies().keys()),
            )
            return True

        except Exception as exc:
            self._is_warmed = False
            logger.warning("Failed during NSE session warm-up: %s", exc)
            return False

    def is_warm(self) -> bool:
        """Checks whether the session is currently warm and within its TTL."""
        if not self._is_warmed or self._session is None:
            return False
        return (time.time() - self._last_warmed) < self.cfg.session_ttl_seconds

    def get_cookies(self) -> Dict[str, str]:
        """Returns the dictionary of currently harvested session cookies."""
        if self._session is None:
            return {}
        try:
            return dict(self._session.cookies)
        except Exception:
            return {}

    def get(self, url: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> Any:
        """Executes a GET request using the warmed session with auto-recovery on 401/403.

        Args:
            url: Target URL.
            headers: Optional request-specific headers to merge.
            **kwargs: Additional parameters forwarded to session.get().

        Returns:
            The HTTP response object.

        Raises:
            NSEConnectionError, NSESessionExpiredError, NSERateLimitError
        """
        if not self.is_warm():
            if not self.warm_up():
                raise NSESessionExpiredError("Could not warm up session with NSE India.")

        req_headers = dict(self._session.headers)
        if headers:
            req_headers.update(headers)

        kwargs.setdefault("timeout", self.cfg.request_timeout)

        try:
            response = self._session.get(url, headers=req_headers, **kwargs)
        except Exception as e:
            raise NSEConnectionError(f"Network error querying {url}: {e}") from e

        # Handle session expiration or Cloudflare/Akamai challenge
        if response.status_code in (401, 403):
            logger.warning("Received HTTP %d from %s. Re-warming session...", response.status_code, url)
            if self.warm_up(force=True):
                req_headers = dict(self._session.headers)
                if headers:
                    req_headers.update(headers)
                try:
                    response = self._session.get(url, headers=req_headers, **kwargs)
                except Exception as e:
                    raise NSEConnectionError(f"Network error on retry querying {url}: {e}") from e

            if response.status_code in (401, 403):
                raise NSESessionExpiredError(
                    f"NSE access denied (HTTP {response.status_code}) for {url}. "
                    "Session warm-up did not satisfy anti-bot requirements."
                )

        if response.status_code == 429:
            raise NSERateLimitError(f"NSE rate limit encountered (HTTP 429) for {url}")

        return response

    def close(self):
        """Closes the underlying HTTP session."""
        if self._session is not None:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None
            self._is_warmed = False
