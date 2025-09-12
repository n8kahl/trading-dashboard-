import logging
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))


def test_server_exits_when_api_key_missing(monkeypatch, caplog):
    monkeypatch.delenv("POLYGON_API_KEY", raising=False)
    dummy_fastmcp = types.ModuleType("fastmcp")

    class DummyMCP:
        def __init__(self, *args, **kwargs):
            pass

        def run(self, *args, **kwargs):
            pass

    dummy_fastmcp.FastMCP = DummyMCP
    dummy_fastmcp.tool = lambda f: f
    sys.modules["fastmcp"] = dummy_fastmcp
    with caplog.at_level(logging.ERROR):
        sys.modules.pop("mcp_server.server", None)
        with pytest.raises(SystemExit):
            import mcp_server.server  # noqa: F401
    sys.modules.pop("mcp_server.server", None)
    sys.modules.pop("fastmcp", None)
    assert "POLYGON_API_KEY not set" in caplog.text
