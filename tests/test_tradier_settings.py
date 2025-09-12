import asyncio
import pytest
import asyncio
import pytest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.core.settings import settings
from app.services import tradier_client, options_picker, tradier
from app.routers import broker_tradier
from fastapi import HTTPException


def test_tradier_client_missing_token(monkeypatch):
    import asyncio
    monkeypatch.setattr(settings, 'TRADIER_ACCESS_TOKEN', None)
    with pytest.raises(tradier_client.TradierError):
        asyncio.run(tradier_client.get('/test'))


def test_options_picker_missing_token(monkeypatch):
    import asyncio
    monkeypatch.setattr(settings, 'TRADIER_ACCESS_TOKEN', None)
    result = asyncio.run(options_picker.pick_options('AAPL', 'call', 0, 1, 1))
    assert result['ok'] is False


def test_broker_headers_missing_token(monkeypatch):
    monkeypatch.setattr(settings, 'TRADIER_ACCESS_TOKEN', None)
    with pytest.raises(HTTPException):
        broker_tradier._headers()


def test_account_overview_missing_account(monkeypatch):
    import asyncio
    monkeypatch.setattr(settings, 'TRADIER_ACCESS_TOKEN', 'token')
    monkeypatch.setattr(settings, 'TRADIER_ACCOUNT_ID', None)
    with pytest.raises(HTTPException):
        asyncio.run(broker_tradier.account_overview())


def test_tradier_batch_quotes_missing_token(monkeypatch):
    monkeypatch.setattr(settings, 'TRADIER_ACCESS_TOKEN', None)
    assert tradier.tradier_batch_option_quotes(['AAPL']) == {}
