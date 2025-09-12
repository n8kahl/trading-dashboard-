#!/usr/bin/env python3
import getpass
import sys
from pathlib import Path

import httpx

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def prompt(label, optional=False, default=None, secret=False):
    val = getpass.getpass(label + ": ") if secret else input(label + (f" [{default}]" if default else "") + ": ")
    if not val and default is not None:
        return default
    if not val and optional:
        return ""
    if not val:
        print("Please enter a value.")
        return prompt(label, optional, default, secret)
    return val


def validate_polygon_key(key: str) -> bool:
    # Official aggregates endpoint per docs (we only validate the key with a simple call)
    url = "https://api.polygon.io/v2/aggs/ticker/SPY/range/1/minute/2024-01-02/2024-01-02"
    try:
        r = httpx.get(url, params={"apiKey": key, "limit": 1, "sort": "desc"}, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"[!] Polygon validation error: {e}")
        return False


def main():
    print("\n=== Trading Assistant (MCP-ready) Setup ===\n")
    poly = prompt("POLYGON_API_KEY", secret=True)
    if not validate_polygon_key(poly):
        print("\n[!] Polygon API key validation failed against official endpoint. Check your key.\n")
        sys.exit(1)
    tradier_token = prompt("TRADIER_ACCESS_TOKEN (optional)", optional=True, secret=True)
    tradier_acct = prompt("TRADIER_ACCOUNT_ID (optional)", optional=True)
    tradier_env = prompt("TRADIER_ENV [sandbox|production] (optional)", optional=True, default="sandbox")
    db_url = prompt("DATABASE_URL (leave blank for SQLite)", optional=True)
    tz = prompt("APP_TIMEZONE", default="America/Chicago")

    ENV_PATH.write_text(
        "\\n".join(
            [
                f"POLYGON_API_KEY={poly}",
                f"TRADIER_ACCESS_TOKEN={tradier_token}",
                f"TRADIER_ACCOUNT_ID={tradier_acct}",
                f"TRADIER_ENV={tradier_env}",
                f"DATABASE_URL={db_url}",
                f"APP_TIMEZONE={tz}",
            ]
        )
        + "\\n"
    )
    print(f"\n[ok] Wrote {ENV_PATH}\n")


if __name__ == "__main__":
    main()
