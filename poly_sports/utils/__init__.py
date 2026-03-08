import asyncio
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

_run_wrapper()