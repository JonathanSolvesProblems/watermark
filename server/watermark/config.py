"""Settings from environment variables. `MODE=mock` runs everything with no Ring
credentials, no AWS and no hardware; that is the mode tests and the first local
run use. Everything else flips one backend at a time."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    return v if v not in (None, "") else default


def _env_int(name: str, default: int) -> int:
    v = _env(name)
    return int(v) if v else default


def _env_bool(name: str, default: bool = False) -> bool:
    v = _env(name)
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes", "on")


@dataclass
class Settings:
    mode: str = "mock"                      # mock | live | playground
    data_dir: Path = field(default_factory=lambda: Path(_env("DATA_DIR", "data")))
    public_base_url: str = "http://localhost:8000"
    web_origin: str = "http://localhost:3000"
    dev_tools: bool = True                  # exposes /api/test/* (always on in mock)

    # Ring partner credentials (Developer Portal)
    ring_client_id: str | None = None
    ring_client_secret: str | None = None
    ring_hmac_key: str = "mock-signing-key"
    ring_api_base: str = "https://api.amazonvision.com"

    # capture
    capture_backend: str = "mock"           # mock | whep
    capture_download_fallback: bool = True  # off for the Playground, whose token cannot download media
    playground_token_file: str = "../tmp/playground_token.txt"  # Ring Developer Playground: a 30-minute token pasted here
    capture_interval_s: int = 300           # between capture sessions while the sensor is faulted
    capture_session_s: int = 55             # under the 60 s line-powered cap
    capture_fps: float = 1.0
    first_capture_delay_s: int = 0

    # captions (AWS Builder)
    captions_backend: str = "mock"          # mock | bedrock
    bedrock_model_id: str = "amazon.nova-lite-v1:0"
    aws_region: str = "us-east-1"

    # blobs
    blob_backend: str = "local"             # local | s3
    s3_bucket: str | None = None

    # rover dispatch
    dispatch_backend: str = "local"         # local | iot
    iot_endpoint: str | None = None         # xxxx-ats.iot.<region>.amazonaws.com
    iot_topic_prefix: str = "watermark/rover"
    rover_token: str = "dev-rover-token"    # shared secret the rover sends on /rover/*
    rover_wait_s: int = 90                  # give the rover this long to reach station before capturing anyway

    # brain (aftermath findings)
    brain_backend: str = "mock"             # mock | bedrock | ollama | claude

    # reconciliation
    reconcile_interval_s: int = 60

    @classmethod
    def from_env(cls) -> "Settings":
        mode = _env("MODE", "mock") or "mock"
        s = cls(
            mode=mode,
            data_dir=Path(_env("DATA_DIR", "data") or "data"),
            public_base_url=_env("PUBLIC_BASE_URL", "http://localhost:8000") or "http://localhost:8000",
            web_origin=_env("WEB_ORIGIN", "http://localhost:3000") or "http://localhost:3000",
            dev_tools=_env_bool("DEV_TOOLS", mode in ("mock", "playground")),
            ring_client_id=_env("RING_CLIENT_ID"),
            ring_client_secret=_env("RING_CLIENT_SECRET"),
            ring_hmac_key=_env("RING_HMAC_KEY", "mock-signing-key") or "mock-signing-key",
            ring_api_base=_env("RING_API_BASE", "https://api.amazonvision.com") or "https://api.amazonvision.com",
            capture_backend=_env("CAPTURE_BACKEND", "mock" if mode == "mock" else "whep") or "mock",
            capture_interval_s=_env_int("CAPTURE_INTERVAL_S", 300),
            capture_session_s=_env_int("CAPTURE_SESSION_S", 55),
            capture_fps=float(_env("CAPTURE_FPS", "1.0") or 1.0),
            capture_download_fallback=_env_bool("CAPTURE_DOWNLOAD_FALLBACK", mode != "playground"),
            playground_token_file=_env("RING_PLAYGROUND_TOKEN_FILE", "../tmp/playground_token.txt") or "../tmp/playground_token.txt",
            first_capture_delay_s=_env_int("FIRST_CAPTURE_DELAY_S", 0),
            captions_backend=_env("CAPTIONS_BACKEND", "mock") or "mock",
            bedrock_model_id=_env("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0") or "amazon.nova-lite-v1:0",
            aws_region=_env("AWS_REGION", "us-east-1") or "us-east-1",
            blob_backend=_env("BLOB_BACKEND", "local") or "local",
            s3_bucket=_env("S3_BUCKET"),
            dispatch_backend=_env("DISPATCH_BACKEND", "local") or "local",
            iot_endpoint=_env("IOT_ENDPOINT"),
            iot_topic_prefix=_env("IOT_TOPIC_PREFIX", "watermark/rover") or "watermark/rover",
            rover_token=_env("ROVER_TOKEN", "dev-rover-token") or "dev-rover-token",
            rover_wait_s=_env_int("ROVER_WAIT_S", 90),
            brain_backend=_env("BRAIN_BACKEND", "mock") or "mock",
            reconcile_interval_s=_env_int("RECONCILE_INTERVAL_S", 60),
        )
        return s

    @property
    def is_mock(self) -> bool:
        return self.mode == "mock"

    @property
    def is_playground(self) -> bool:
        return self.mode == "playground"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "watermark.sqlite"

    @property
    def blob_dir(self) -> Path:
        return self.data_dir / "blobs"
