# Fail-Open Decorator

`fail_open` wraps FastAPI endpoints so that unexpected exceptions return
fallback data instead of propagating errors. The decorator supports both
synchronous and asynchronous handlers and is controlled by the
`TA_FAIL_OPEN` environment variable (set to `0` to disable).

## Synchronous example

```python
from app.core.failopen import fail_open

@fail_open(lambda: {"positions": []})
def load_positions():
    raise RuntimeError("database offline")

print(load_positions())
# {'positions': [], 'ok': False, 'note': 'fallback due to error: RuntimeError'}
```

## Asynchronous example

```python
from app.core.failopen import fail_open
import asyncio

@fail_open(lambda: {"positions": []})
async def load_positions_async():
    raise RuntimeError("database offline")

asyncio.run(load_positions_async())
# {'positions': [], 'ok': False, 'note': 'fallback due to error: RuntimeError'}
```
