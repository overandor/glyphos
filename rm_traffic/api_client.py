"""
RentMasseur API Client — bounded, production-ready HTTP client.

Confirmed endpoints only. No guesswork. No spam.
"""

import json
import logging
import re
import time
from typing import Optional, Dict, Any

import requests

log = logging.getLogger("rm_api")

BASE = "https://rentmasseur.com"
API = f"{BASE}/api/v1"


class RentMasseurAPI:
    """Direct API client for rentmasseur.com using confirmed endpoints."""

    def __init__(self, min_request_interval: float = 2.0):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": f"{BASE}/settings",
            "Origin": BASE,
        })
        self.csrf = None
        self.logged_in = False
        self.username = None
        self.last_request = 0.0
        self.min_request_interval = min_request_interval

    def _wait(self):
        """Respectful rate limiting between requests."""
        elapsed = time.time() - self.last_request
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request = time.time()

    def _get(self, path: str, params: Optional[Dict] = None) -> requests.Response:
        self._wait()
        return self.session.get(f"{API}{path}", params=params, timeout=15)

    def _post(self, path: str, json_data: Dict) -> requests.Response:
        self._wait()
        return self.session.post(f"{API}{path}", json=json_data, timeout=15)

    def _put(self, path: str, json_data: Dict) -> requests.Response:
        self._wait()
        return self.session.put(f"{API}{path}", json=json_data, timeout=15)

    def _get_csrf(self) -> str:
        resp = self.session.get(f"{BASE}/login")
        m = re.search(r'csrf["\s:=]+([A-Za-z0-9+/=]{20,})', resp.text)
        if m:
            self.csrf = m.group(1)
            return self.csrf
        for cookie in self.session.cookies:
            if "csrf" in cookie.name.lower() or "token" in cookie.name.lower():
                self.csrf = cookie.value
                return self.csrf
        return ""

    def login(self, username: str, password: str) -> bool:
        """Login via API and store bearer token."""
        self.username = username
        csrf = self._get_csrf()
        self._wait()
        resp = self.session.post(f"{API}/login", json={
            "email": username,
            "password": password,
            "csrf": csrf,
            "remember": True,
        })
        if resp.status_code != 200:
            log.error("Login failed: %d %s", resp.status_code, resp.text[:200])
            return False
        try:
            data = resp.json()
        except Exception:
            log.error("Login response not JSON (captcha/block?): %s", resp.text[:300])
            return False
        token = data.get("accessToken")
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        self.logged_in = True
        log.info("Login OK as %s", username)
        return True

    def load_cookies(self, cookies: list):
        """Load cookies from a saved session (e.g. from Selenium)."""
        for c in cookies:
            self.session.cookies.set(c["name"], c["value"], domain=c.get("domain", ""), path=c.get("path", "/"))
        self.logged_in = True

    # ------------------------------------------------------------------
    # Confirmed read endpoints
    # ------------------------------------------------------------------

    def get_dashboard(self) -> Dict:
        resp = self._get("/account/dashboard")
        resp.raise_for_status()
        return resp.json()

    def get_availability(self) -> Dict:
        resp = self._get("/account/dashboard/availability")
        resp.raise_for_status()
        return resp.json()

    def set_availability(self, option: int = 1, duration: int = 5) -> Dict:
        """
        Set availability.
        option: 0=Not Set, 1=Available, 2=Not Available
        duration: index from timePeriods (0=1h, 1=2h, ..., 5=6h)
        """
        resp = self._put("/account/dashboard/availability", {"option": option, "duration": duration})
        resp.raise_for_status()
        return resp.json()

    def get_ad_statistics(self) -> Dict:
        resp = self._get("/account/dashboard/ad-statistics")
        resp.raise_for_status()
        return resp.json()

    def get_keeponline(self) -> Dict:
        resp = self._get("/account/keeponline")
        resp.raise_for_status()
        return resp.json()

    def get_about(self) -> Dict:
        resp = self._get("/settings/about")
        resp.raise_for_status()
        return resp.json()

    def get_mailbox(self, page: int = 1, folder: int = 1, sort: int = 1) -> Dict:
        resp = self._get("/mailbox", params={"page": page, "folder": folder, "sort": sort})
        resp.raise_for_status()
        return resp.json()

    def get_blogs(self, page: int = 1) -> Dict:
        resp = self._get("/blogs", params={"page": page})
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Confirmed write endpoints
    # ------------------------------------------------------------------

    def set_visibility(self, visible: bool) -> Dict:
        resp = self._put("/settings/visibility", {"isAdHidden": not visible})
        resp.raise_for_status()
        return resp.json()

    def set_sms_alerts(self, enabled: bool) -> Dict:
        resp = self._put("/settings/sms", {"sms": enabled})
        resp.raise_for_status()
        return resp.json()

    def set_track_actions(self, enabled: bool) -> Dict:
        resp = self._put("/settings/track-actions", {"trackActions": enabled})
        resp.raise_for_status()
        return resp.json()

    def set_about(self, headline: str, description: str) -> Dict:
        resp = self._put("/settings/about", {"headline": headline, "description": description})
        resp.raise_for_status()
        try:
            return resp.json()
        except Exception:
            return {"status": "ok", "raw": resp.text[:500]}

    # ------------------------------------------------------------------
    # Search (read-only)
    # ------------------------------------------------------------------

    def search(self, city: str = "manhattan-ny", available_only: bool = False,
               page: int = 1, skip: int = 0) -> Dict:
        body = {"searchCity": city, "page": page, "skipUsers": str(skip)}
        if available_only:
            body["available"] = 1
        resp = self._post("/search", body)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Full status
    # ------------------------------------------------------------------

    def full_status(self) -> Dict:
        return {
            "dashboard": self.get_dashboard(),
            "availability": self.get_availability(),
            "stats": self.get_ad_statistics(),
            "keeponline": self.get_keeponline(),
            "about": self.get_about(),
        }
