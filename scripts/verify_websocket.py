#!/usr/bin/env python3
import asyncio
import sys
from typing import Any

import socketio

sio: socketio.AsyncClient = socketio.AsyncClient()  # type: ignore[assignment]
received_event = asyncio.Event()


@sio.event  # type: ignore[misc]
async def connect() -> None:
    print("✅ WebSocket Connected")


@sio.event  # type: ignore[misc]
async def connect_error(data: Any) -> None:
    print(f"❌ WebSocket Connect Error: {data}")


@sio.event  # type: ignore[misc]
async def live_metrics(data: Any) -> None:
    print(f"⚡ live_metrics received: {data}")
    if data and ("load_kw" in data or "pv_kw" in data):
        print("🎉 Validation Successful: Live power data flowing!")
        received_event.set()
    else:
        print("⚠️ Received empty/invalid metrics")


async def main() -> None:
    print("🔍 Starting WebSocket Verification...")
    try:
        await sio.connect("http://localhost:5000")  # type: ignore[attr-defined]

        # Wait for event with timeout
        try:
            await asyncio.wait_for(received_event.wait(), timeout=10.0)
            print("✅ WebSocket verification passed.")
            await sio.disconnect()  # type: ignore[attr-defined]
            sys.exit(0)
        except TimeoutError:
            print("❌ WebSocket Validation Timed Out (No live_metrics received)")
            await sio.disconnect()  # type: ignore[attr-defined]
            sys.exit(1)

    except Exception as e:
        print(f"❌ WebSocket Client Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
