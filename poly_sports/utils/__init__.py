import asyncio
import os

from .logger import logger
from .logger import _main as _main_logger
from .wrapper import wrapper

__all__ = ['logger', 'main', 'wrapper']


def _run_wrapper() -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is None:
        asyncio.run(wrapper())
    else:
        loop.create_task(wrapper())


def run_wrapper() -> None:
    """Run the optional async wrapper (not executed on package import)."""
    _run_wrapper()


# Importing poly_sports.utils must not block (tests, CLI, libraries). Opt-in only.
if os.environ.get("POLY_SPORTS_AUTORUN_WRAPPER", "").strip().lower() in ("1", "true", "yes"):
    _run_wrapper()
