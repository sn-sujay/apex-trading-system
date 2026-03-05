# APEX Trading Intelligence System — root package
__version__ = "1.0.0"
__author__ = "APEX Trading"
__description__ = "Indian & Global AI Trading Intelligence System"

from .core import SignalSchema, Config
from .api import create_app

__all__ = ["SignalSchema", "Config", "create_app", "__version__"]
