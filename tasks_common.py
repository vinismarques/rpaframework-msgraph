"""Common Invoke tasks.py helpers."""

import platform
import re
from glob import glob
from pathlib import Path


def poetry(ctx, command, **kwargs):
    kwargs.setdefault("echo", True)
    if platform.system() != "Windows":
        kwargs.setdefault("pty", True)

    return ctx.run(f"poetry {command}", **kwargs)
