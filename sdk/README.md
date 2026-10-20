# ringwire

A typed Python client for the **Ring Partner API** (the `api.amazonvision.com` API behind the
Ring Appstore), including the parts most samples skip: sensors, the two-step media
downloads, chime playback, webhook verification, and the account-linking nonce.

Built for [Watermark](../README.md) and published on its own so other Ring Appstore
developers do not have to re-read the docs I already read.

```bash
pip install ringwire
```

## What it covers

| Area | Calls |
|---|---|
| Auth | `RingClient.exchange_code`, `RingClient.refresh` (form-encoded, as Ring requires) |
| Users and linking | `me()`, `confirm_account_link(nonce)`, `update_integration(status="completed")` |
| Devices | `list_devices()`, `status()`, `capabilities()`, `configurations()`, `location()` |
| Sensors | `status()` exposes `flood_faulted`, `freeze_faulted`, `contact_faulted`, `tamper_detected`, `temperature`, `humidity`; `reported_at` is `None` for the 1970 "never reported" epoch |
| History | `event_history()`, `iter_event_history()` (follows `links.next`, stops on the empty page) |
| Media | `download_image()` and `download_clip()` do the 303 two-step and read `X-Media-Timestamp` / `X-Media-Origin` |
| Live | `create_whep_session()`, `close_whep_session()`, `rtsps_url()` |
| Chimes | `play_chime(device_id, audio_ref)`, with slots read from `configurations()` |
| Webhooks | `verify_signature`, `verify_and_parse`, `parse_event`, `make_event`, every documented event type including the Early Access sensor events |
| Nonce | `compute_nonce`, `match_nonce` (URL-safe base64, no padding, 600 s window, constant-time) |

## Things the docs say that this library enforces

- The image and clip endpoints **never trigger a capture**. A `416` raises `MediaNotFound`
  so the caller can start a live session first.
- Sensor events have **no history endpoint**. Persist them on receipt.
- Webhook signatures are computed over the **raw body bytes**. Pass the bytes, not the
  parsed JSON.
- Refresh tokens are not Bearer tokens.

## Example

```python
from ringwire import RingClient, verify_and_parse

client = RingClient(access_token)
sensors = [d for d in client.list_devices() if client.status(d.id).flood_faulted is not None]

# In your webhook handler (raw bytes, before any JSON parsing):
event = verify_and_parse(raw_body, headers["X-Signature"], signing_key)
if event.type == "flood_detected":
    ...
```

## Tests

```bash
pip install -e ".[dev]" && pytest
```

MIT. Not affiliated with Ring or Amazon.
