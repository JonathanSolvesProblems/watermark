import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from watermark.app import create_app
from watermark.config import Settings
from watermark.ring import MockRing


@pytest.fixture
def settings(tmp_path):
    return Settings(mode="mock", data_dir=tmp_path / "data", dev_tools=True, capture_interval_s=1,
                    capture_session_s=2, capture_fps=2.0, rover_wait_s=2, reconcile_interval_s=3600)


@pytest.fixture
def app(settings):
    MockRing._inst = None   # fresh mock account per test
    return create_app(settings)


@pytest.fixture
async def client(app):
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


async def wait_for(pred, timeout=5.0, step=0.05):
    end = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < end:
        v = pred()
        if v:
            return v
        await asyncio.sleep(step)
    return pred()
