"""Questrade API smoke test -- verify token and list accounts (no sensitive data printed)."""

import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

TOKEN_FILE = Path(__file__).resolve().parents[2] / "data" / "questrade_token.json"


def refresh_token(refresh_tok: str) -> dict:
    """Exchange refresh token for access token. Returns full token payload."""
    resp = requests.post(
        "https://login.questrade.com/oauth2/token",
        params={"grant_type": "refresh_token", "refresh_token": refresh_tok},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def save_token(token_data: dict) -> None:
    """Persist token data for future use (refresh tokens are single-use)."""
    import json
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(token_data, indent=2), encoding="utf-8")


def load_saved_token() -> dict | None:
    """Load previously saved token if it exists."""
    import json
    if TOKEN_FILE.exists():
        try:
            return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, KeyError):
            return None
    return None


def get_access_token() -> tuple[str, str]:
    """Get a valid access token. Returns (access_token, api_server)."""
    # Try saved token first
    saved = load_saved_token()
    if saved and saved.get("access_token") and saved.get("api_server"):
        # Test if still valid
        try:
            test_resp = requests.get(
                f"{saved['api_server']}v1/accounts",
                headers={"Authorization": f"Bearer {saved['access_token']}"},
                timeout=10,
            )
            if test_resp.status_code == 200:
                return saved["access_token"], saved["api_server"]
        except requests.RequestException:
            pass
        # Access token expired, try refresh with saved refresh token
        if saved.get("refresh_token"):
            try:
                token_data = refresh_token(saved["refresh_token"])
                save_token(token_data)
                return token_data["access_token"], token_data["api_server"]
            except requests.HTTPError:
                pass  # Refresh token also expired, fall through to env

    # Use env refresh token (initial setup or recovery)
    env_token = os.environ.get("QUESTRADE_REFRESH_TOKEN", "").strip()
    if not env_token:
        print("ERROR: QUESTRADE_REFRESH_TOKEN not set in .env")
        sys.exit(1)

    token_data = refresh_token(env_token)
    save_token(token_data)
    print("Token refreshed and saved to data/questrade_token.json")
    print("NOTE: The refresh token in .env is now expired (single-use).")
    print("      Future calls will use the saved token file automatically.")
    return token_data["access_token"], token_data["api_server"]


def main():
    print("Questrade API Smoke Test")
    print("-" * 40)

    try:
        access_token, api_server = get_access_token()
    except requests.HTTPError as e:
        print(f"ERROR: Token refresh failed: {e}")
        print("The refresh token may be expired or already used.")
        print("Generate a new one at: https://www.questrade.com/api")
        sys.exit(1)

    print(f"API Server: {api_server}")
    print("Authentication: OK")

    # Get accounts (just count and types, no sensitive data)
    resp = requests.get(
        f"{api_server}v1/accounts",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    resp.raise_for_status()
    accounts = resp.json().get("accounts", [])

    print(f"Accounts found: {len(accounts)}")
    for acct in accounts:
        acct_type = acct.get("type", "unknown")
        acct_status = acct.get("status", "unknown")
        # Show account number partially masked
        acct_num = acct.get("number", "???")
        masked = acct_num[:2] + "***" + acct_num[-2:] if len(acct_num) > 4 else "****"
        print(f"  - {masked} | Type: {acct_type} | Status: {acct_status}")

    # Quick positions count per account (no ticker details)
    for acct in accounts:
        acct_id = acct.get("number", "")
        pos_resp = requests.get(
            f"{api_server}v1/accounts/{acct_id}/positions",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if pos_resp.status_code == 200:
            positions = pos_resp.json().get("positions", [])
            print(f"  - {acct_id[:2]}***: {len(positions)} open position(s)")

    print("-" * 40)
    print("Smoke test PASSED")


if __name__ == "__main__":
    main()
