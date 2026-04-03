"""Require a valid Ethereum/Polygon private key from the environment before running the app."""
import os
import sys
from typing import Callable, Optional

_PK_ENV_KEYS = ("PK", "PRIVATE_KEY")

_PLACEHOLDER_KEYS = frozenset(
    {
        "your_private_key",
        "your_private_key_here",
        "placeholder",
        "changeme",
    }
)


def get_env_private_key() -> Optional[str]:
    for name in _PK_ENV_KEYS:
        val = os.getenv(name)
        if val is not None and val.strip():
            return val.strip()
    return None


def _stop_with_alert(detail: str, log: Optional[Callable[[str], None]], exit_code: int) -> None:
    banner = "=" * 72
    block = (
        f"\n{banner}\n"
        f"  ALERT: Project cannot start — private key missing or invalid\n"
        f"{banner}\n"
        f"  {detail}\n"
        f"  Fix: set PK or PRIVATE_KEY in your .env (64 hex digits, optional 0x prefix).\n"
        f"{banner}\n"
    )
    sys.stderr.write(block)
    sys.stderr.flush()
    if log is not None:
        log(detail)
    sys.exit(exit_code)


def require_valid_env_private_key(
    *,
    log: Optional[Callable[[str], None]] = None,
    exit_code: int = 1,
) -> None:
    """
    Exit the process if PK / PRIVATE_KEY is missing, placeholder, or not a valid key.
    Always prints an ALERT to stderr. Optional ``log`` mirrors the detail line (e.g. logger).
    Call after ``load_dotenv()`` so .env is applied.
    """
    raw = get_env_private_key()
    if not raw:
        _stop_with_alert(
            "No private key found in the environment (PK or PRIVATE_KEY).",
            log,
            exit_code,
        )
    if raw.lower() in _PLACEHOLDER_KEYS:
        _stop_with_alert(
            "PK / PRIVATE_KEY is still a placeholder; replace it with your real key in .env.",
            log,
            exit_code,
        )
    try:
        from eth_account import Account

        Account.from_key(raw)
    except Exception:
        _stop_with_alert(
            "PK / PRIVATE_KEY is not a valid Ethereum-style private key (length, hex, or curve check failed).",
            log,
            exit_code,
        )
