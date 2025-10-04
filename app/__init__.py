"""Application package bootstrap."""

from .compat import ensure_forward_ref_compat

ensure_forward_ref_compat()

__all__ = ["ensure_forward_ref_compat"]
