"""
APEX Trading System -- Tests for trading_system.core.signal_schema
"""
import pytest


def test_signal_schema_imports():
    """signal_schema must import cleanly."""
    from trading_system.core import signal_schema  # noqa: F401


def test_trade_signal_class_exists():
    """TradeSignal (or equivalent) dataclass/model must exist."""
    import trading_system.core.signal_schema as ss
    found = any(hasattr(ss, name) for name in (
        "TradeSignal", "Signal", "OptionSignal", "SignalPayload"
    ))
    assert found, "No signal class found in signal_schema"


def test_signal_direction_constants():
    """BUY/SELL or LONG/SHORT constants must be defined."""
    import trading_system.core.signal_schema as ss
    has_direction = (
        hasattr(ss, "BUY") or hasattr(ss, "SELL") or
        hasattr(ss, "LONG") or hasattr(ss, "SHORT") or
        hasattr(ss, "Direction") or hasattr(ss, "SignalDirection")
    )
    assert has_direction, "No direction constants/enum found in signal_schema"


def test_constants_imports():
    """constants module must import cleanly."""
    from trading_system.core import constants  # noqa: F401


def test_constants_has_nse_symbols():
    """constants must define NSE instrument symbols."""
    from trading_system.core import constants as c
    has_symbols = (
        hasattr(c, "NIFTY") or hasattr(c, "NIFTY_50") or
        hasattr(c, "BANKNIFTY") or hasattr(c, "NSE_INDICES") or
        hasattr(c, "INSTRUMENTS")
    )
    assert has_symbols, "No NSE symbol constants found"


def test_constants_has_exchange_constant():
    """constants must define NSE/BSE exchange identifier."""
    from trading_system.core import constants as c
    has_exchange = (
        hasattr(c, "NSE") or hasattr(c, "BSE") or
        hasattr(c, "EXCHANGE_NSE") or hasattr(c, "EXCHANGE")
    )
    assert has_exchange, "No exchange constant found in constants"
