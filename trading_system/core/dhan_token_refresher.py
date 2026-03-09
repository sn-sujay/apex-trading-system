"""
dhan_token_refresher.py
-----------------------
APEX Trading System -- Dhan Access Token Auto-Renewal
Calls GET https://api.dhan.co/v2/RenewToken with the current active token.
Returns a new token valid for 24 hours and writes it to Nebula memory
under key DHAN_ACCESS_TOKEN so all APEX agents pick it up instantly.

Usage:
    python dhan_token_refresher.py

Environment variables required:
    DHAN_ACCESS_TOKEN   -- current active JWT token
    DHAN_CLIENT_ID      -- your Dhan client ID (numeric string)

Called automatically by the APEX Token Auto-Renew trigger daily at 08:00 IST.
"""

import os
import sys
import json
import logging
import base64
import httpx
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
RENEW_URL = "https://api.dhan.co/v2/RenewToken"
TIMEOUT_SECONDS = 15
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
log = logging.getLogger("dhan_token_refresher")


# ---------------------------------------------------------------------------
# Health check -- decode JWT and log time-to-expiry (no signature verification)
# ---------------------------------------------------------------------------
def check_token_age(access_token: str) -> None:
    try:
        payload_b64 = access_token.split(".")[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))

        exp_ts = payload.get("exp")
        if exp_ts:
            exp_dt = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
            now = datetime.now(timezone.utc)
            hours_left = (exp_dt - now).total_seconds() / 3600

            log.info(
                "Token expires at %s UTC (%.1f hours remaining)",
                exp_dt.strftime("%Y-%m-%d %H:%M"),
                hours_left,
            )

            if hours_left < 0:
                log.error("Token is ALREADY EXPIRED -- renewal will fail.")
            elif hours_left < 2:
                log.warning("Token expires in < 2 hours -- renewing now.")
            else:
                log.info("Token healthy -- renewing proactively to reset 24h clock.")
    except Exception as exc:
        log.warning("Could not decode token age: %s", exc)


# ---------------------------------------------------------------------------
# Core renewal call
# ---------------------------------------------------------------------------
def renew_dhan_token(access_token: str, client_id: str) -> dict:
    """
    Call Dhan RenewToken and return the full response dict.
    Raises ValueError on 401, httpx errors on network/HTTP failures.
    """
    headers = {
        "access-token": access_token,
        "dhanClientId": client_id,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    log.info("Calling Dhan RenewToken for client %s ...", client_id)

    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        response = client.get(RENEW_URL, headers=headers)

    if response.status_code == 401:
        raise ValueError(
            "Token expired or invalid -- cannot renew. "
            "Generate a fresh token from web.dhan.co and update DHAN_ACCESS_TOKEN."
        )

    response.raise_for_status()

    data = response.json()
    new_token = data.get("accessToken")
    if not new_token:
        raise ValueError(
            f"RenewToken response missing 'accessToken' field: {data}"
        )

    log.info("Token renewed. New expiry: %s", data.get("expiryTime", "unknown"))
    return data


# ---------------------------------------------------------------------------
# Emit structured output for Nebula orchestrator to write to memory
# ---------------------------------------------------------------------------
def emit_memory_update(new_token: str, expiry: str) -> None:
    output = {
        "action": "UPDATE_MEMORY",
        "key": "DHAN_ACCESS_TOKEN",
        "value": new_token,
        "expiry_time": expiry,
        "renewed_at": datetime.now(timezone.utc).isoformat(),
    }
    print(json.dumps(output, indent=2))
    log.info("Memory update payload emitted for DHAN_ACCESS_TOKEN")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    access_token = os.getenv("DHAN_ACCESS_TOKEN", "").strip()
    client_id = os.getenv("DHAN_CLIENT_ID", "").strip()

    if not access_token:
        log.error("DHAN_ACCESS_TOKEN environment variable is not set.")
        return 1
    if not client_id:
        log.error("DHAN_CLIENT_ID environment variable is not set.")
        return 1

    check_token_age(access_token)

    try:
        result = renew_dhan_token(access_token, client_id)
        new_token = result["accessToken"]
        expiry = result.get("expiryTime", "unknown")
        emit_memory_update(new_token, expiry)
        log.info(
            "=== APEX Token Renewal SUCCESS === Client: %s | Expiry: %s",
            result.get("dhanClientId"),
            expiry,
        )
        return 0

    except ValueError as exc:
        log.error("Auth error: %s", exc)
        return 1
    except httpx.HTTPStatusError as exc:
        log.error("HTTP %s: %s", exc.response.status_code, exc.response.text)
        return 1
    except httpx.RequestError as exc:
        log.error("Network error: %s", exc)
        return 1
    except Exception as exc:
        log.exception("Unexpected error: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
