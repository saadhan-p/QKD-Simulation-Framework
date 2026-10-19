"""
Async WebSocket QKD client.

Provides QKDClient which connects to a backend WebSocket and streams messages.
Requires `websockets` (or you can swap to `websocket-client` / httpx if preferred).
"""

import asyncio
import json
from typing import Callable, Optional

import websockets


class QKDClient:
    """
    Simple WebSocket client for QKD backend.

    Usage:
        client = QKDClient("ws://localhost:8000/ws")
        await client.simulate(params, on_message)
    """

    def __init__(self, ws_url: str, timeout: Optional[float] = 10.0):
        self.ws_url = ws_url
        self.timeout = timeout
        self._ws = None

    async def _connect(self):
        self._ws = await websockets.connect(self.ws_url, ping_interval=20, ping_timeout=10)

    async def simulate(self, params: dict, on_message: Callable[[dict], None]):
        """
        Connect and send a simulation command, then call on_message for each JSON message.

        Args:
            params: dict of simulation parameters (protocol, raw_key_length, qber, etc)
            on_message: callback called with the parsed JSON message for each message from server
        """
        try:
            await self._connect()
            # send simulate command
            cmd = {"cmd": "simulate", "params": params}
            await self._ws.send(json.dumps(cmd))

            async for raw in self._ws:
                try:
                    data = json.loads(raw)
                except Exception:
                    data = {"raw": raw}
                # call the provided callback (sync function) - user should be thread-safe
                on_message(data)

                # Stop if backend says done
                if isinstance(data, dict) and data.get("status") == "done":
                    break
        finally:
            if self._ws:
                await self._ws.close()
                self._ws = None

    async def close(self):
        if self._ws:
            await self._ws.close()
            self._ws = None
