"""Simple logging helper."""

import logging

logger = logging.getLogger("cse")
logging.basicConfig(level=logging.INFO)

__all__ = ["logger"]
