"""Rover dispatch. Two transports, one shape:

- `local`: an in-process queue the rover long-polls over HTTP (`GET /rover/commands`).
  Works on a LAN with nothing else installed. This is what the demo can run on.
- `iot`: publish the command to AWS IoT Core over MQTT (the rover is a Thing
  subscribed to `<prefix>/<rover_id>/commands`). Reports still come back over
  HTTPS to `/rover/report` so a NAT'd Pi never needs an inbound port.

Commands are small JSON documents: {"cmd": "dispatch", "incident_id", "route_id",
"sensor_device_id", "room", "issued_ms"} and {"cmd": "return_home", ...}.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

from .db import now_ms


@dataclass
class Command:
    cmd: str
    incident_id: str | None
    route_id: str | None
    sensor_device_id: str | None
    room: str | None
    issued_ms: int = field(default_factory=now_ms)
    rover_id: str = "rover-1"

    def to_json(self) -> dict[str, Any]:
        return {"cmd": self.cmd, "incident_id": self.incident_id, "route_id": self.route_id,
                "sensor_device_id": self.sensor_device_id, "room": self.room, "issued_ms": self.issued_ms,
                "rover_id": self.rover_id}


class Dispatcher:
    async def send(self, command: Command) -> None:
        raise NotImplementedError

    async def next_command(self, rover_id: str, wait_s: float) -> Command | None:
        """Only the local transport serves this; IoT rovers subscribe instead."""
        return None


class LocalDispatcher(Dispatcher):
    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[Command]] = {}
        self.sent: list[Command] = []

    def _q(self, rover_id: str) -> asyncio.Queue[Command]:
        if rover_id not in self._queues:
            self._queues[rover_id] = asyncio.Queue()
        return self._queues[rover_id]

    async def send(self, command: Command) -> None:
        self.sent.append(command)
        await self._q(command.rover_id).put(command)

    async def next_command(self, rover_id: str, wait_s: float) -> Command | None:
        try:
            return await asyncio.wait_for(self._q(rover_id).get(), timeout=wait_s)
        except asyncio.TimeoutError:
            return None


class IoTDispatcher(Dispatcher):
    """Publishes over MQTT using the AWS IoT Device SDK v2 with SigV4 (server-side
    credentials). Imported lazily so mock mode never loads awscrt."""

    def __init__(self, endpoint: str, topic_prefix: str, region: str, client_id: str = "watermark-server"):
        from awscrt import auth, mqtt  # noqa: F401
        from awsiot import mqtt_connection_builder

        cred = auth.AwsCredentialsProvider.new_default_chain()
        self.conn = mqtt_connection_builder.websockets_with_default_aws_signing(
            endpoint=endpoint, region=region, credentials_provider=cred, client_id=client_id,
            clean_session=True, keep_alive_secs=30)
        self.conn.connect().result()
        self.prefix = topic_prefix.rstrip("/")

    async def send(self, command: Command) -> None:
        from awscrt import mqtt
        topic = f"{self.prefix}/{command.rover_id}/commands"
        fut, _ = self.conn.publish(topic=topic, payload=json.dumps(command.to_json()), qos=mqtt.QoS.AT_LEAST_ONCE)
        await asyncio.to_thread(fut.result, 10)


def make_dispatcher(settings) -> Dispatcher:
    if settings.dispatch_backend == "iot" and settings.iot_endpoint:
        return IoTDispatcher(settings.iot_endpoint, settings.iot_topic_prefix, settings.aws_region)
    return LocalDispatcher()
