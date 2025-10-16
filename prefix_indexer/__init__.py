"""Offline prefix index package."""

from .api import PrefixIndexAPI, PrefixIndexConfig
from .service_http import create_app

__all__ = ["PrefixIndexAPI", "PrefixIndexConfig", "create_app"]

__version__ = "0.1.0"
