"""Compatibility helpers for runtime quirks."""

from __future__ import annotations

import sys
from functools import lru_cache
from typing import ForwardRef


@lru_cache(maxsize=1)
def ensure_forward_ref_compat() -> None:
    """Patch ``ForwardRef._evaluate`` for Python 3.12 + Pydantic v1."""

    if sys.version_info < (3, 12):
        return

    original = ForwardRef._evaluate

    def _patched(self, globalns, localns, *args, **kwargs):
        type_params = args[0] if args else None
        recursive_guard = kwargs.get("recursive_guard")
        if recursive_guard is None and len(args) > 1:
            recursive_guard = args[1]
        if recursive_guard is None:
            recursive_guard = set()
        return original(
            self,
            globalns,
            localns,
            type_params,
            recursive_guard=recursive_guard,
        )

    ForwardRef._evaluate = _patched
