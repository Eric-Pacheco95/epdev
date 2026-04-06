"""Questrade API client — read-only position and balance access.

Token lifecycle:
  - Access token: 30 min TTL
  - Refresh token: 3 day TTL, single-use
  - Each refresh yields a new access + refresh pair
  - Token file: data/questrade_token.json (gitignored)

Usage:
    from tools.scripts.lib.questrade import QuestradeClient
    client = QuestradeClient()
    accounts = client.get_accounts()
    positions = client.get_positions(account_id)
    balances = client.get_balances(account_id)
    quotes = client.get_quotes([symbol_id1, symbol_id2])
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_ROOT / ".env")

TOKEN_FILE = _ROOT / "data" / "questrade_token.json"
OAUTH_URL = "https://login.questrade.com/oauth2/token"


class QuestradeAuthError(Exception):
    """Raised when token refresh fails and manual regeneration is needed."""


class QuestradeClient:
    """Read-only Questrade API client with automatic token management."""

    def __init__(self) -> None:
        self._access_token: str | None = None
        self._api_server: str | None = None
        self._token_data: dict = {}
        self._authenticate()

    def _authenticate(self) -> None:
        """Load or refresh tokens to get a valid access token."""
        saved = self._load_token()
        if saved:
            self._token_data = saved
            self._access_token = saved.get("access_token")
            self._api_server = saved.get("api_server")
            # Test if access token is still valid
            if self._test_access():
                return
            # Try refresh with saved refresh token
            if saved.get("refresh_token"):
                try:
                    self._do_refresh(saved["refresh_token"])
                    return
                except QuestradeAuthError:
                    pass

        # Fall back to env token (initial setup or recovery)
        env_token = os.environ.get("QUESTRADE_REFRESH_TOKEN", "").strip()
        if not env_token:
            raise QuestradeAuthError(
                "No valid token found. Generate a new refresh token at "
                "https://www.questrade.com/api and set QUESTRADE_REFRESH_TOKEN in .env"
            )
        self._do_refresh(env_token)

    def _do_refresh(self, refresh_token: str) -> None:
        """Exchange refresh token for new access + refresh pair."""
        try:
            resp = requests.post(
                OAUTH_URL,
                params={"grant_type": "refresh_token", "refresh_token": refresh_token},
                timeout=15,
            )
            resp.raise_for_status()
        except requests.HTTPError as e:
            raise QuestradeAuthError(
                f"Token refresh failed ({e}). The refresh token may be expired. "
                "Generate a new one at https://www.questrade.com/api"
            ) from e
        self._token_data = resp.json()
        self._access_token = self._token_data["access_token"]
        self._api_server = self._token_data["api_server"]
        self._save_token()

    def _test_access(self) -> bool:
        """Test if current access token works."""
        if not self._access_token or not self._api_server:
            return False
        try:
            resp = requests.get(
                f"{self._api_server}v1/accounts",
                headers=self._headers(),
                timeout=10,
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token}"}

    def _get(self, path: str) -> dict[str, Any]:
        """Make authenticated GET request."""
        resp = requests.get(
            f"{self._api_server}{path}",
            headers=self._headers(),
            timeout=15,
        )
        if resp.status_code == 401:
            # Token expired mid-session, try refresh
            if self._token_data.get("refresh_token"):
                self._do_refresh(self._token_data["refresh_token"])
                resp = requests.get(
                    f"{self._api_server}{path}",
                    headers=self._headers(),
                    timeout=15,
                )
        resp.raise_for_status()
        return resp.json()

    def _load_token(self) -> dict | None:
        if TOKEN_FILE.exists():
            try:
                return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return None
        return None

    def _save_token(self) -> None:
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Add timestamp for staleness tracking
        self._token_data["refreshed_at"] = time.time()
        TOKEN_FILE.write_text(
            json.dumps(self._token_data, indent=2), encoding="utf-8"
        )

    def token_age_hours(self) -> float:
        """Hours since last successful token refresh."""
        refreshed = self._token_data.get("refreshed_at", 0)
        if not refreshed:
            return 999.0
        return (time.time() - refreshed) / 3600

    def get_accounts(self) -> list[dict]:
        return self._get("v1/accounts").get("accounts", [])

    def get_positions(self, account_id: str) -> list[dict]:
        return self._get(f"v1/accounts/{account_id}/positions").get("positions", [])

    def get_balances(self, account_id: str) -> dict:
        return self._get(f"v1/accounts/{account_id}/balances")

    def get_quotes(self, symbol_ids: list[int]) -> list[dict]:
        ids_str = ",".join(str(s) for s in symbol_ids)
        return self._get(f"v1/markets/quotes?ids={ids_str}").get("quotes", [])
