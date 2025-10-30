#!/usr/bin/env python3
"""WebSocket server for Figma plugin and MCP communication."""

import asyncio
import json
import logging
import sys
import signal
from typing import Dict, Set, Any

# websockets: используем новый asyncio-неймспейс, при отсутствии — совместимый импорт
try:
    from websockets.asyncio.server import serve  # websockets >= 15
except Exception:  # pragma: no cover
    from websockets.server import serve  # fallback для старых версий
import websockets


# ───────────────────────────── Logging ─────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ──────────────────── Connected clients / channels ─────────────────
# Аннотации без конкретного класса протокола, чтобы избежать DeprecationWarning
clients: Set[Any] = set()
channels: Dict[str, Set[Any]] = {}


async def register_client(websocket: Any) -> None:
    clients.add(websocket)
    logger.info(
        "Client connected from %s. Total clients: %d",
        getattr(websocket, "remote_address", None),
        len(clients),
    )


async def unregister_client(websocket: Any) -> None:
    clients.discard(websocket)
    # убрать из всех каналов и удалить пустые
    to_delete = []
    for name, members in channels.items():
        members.discard(websocket)
        if not members:
            to_delete.append(name)
    for name in to_delete:
        del channels[name]
        logger.info("Removed empty channel: %s", name)

    logger.info(
        "Client disconnected from %s. Total clients: %d",
        getattr(websocket, "remote_address", "unknown"),
        len(clients),
    )


async def join_channel(websocket: Any, channel: str) -> None:
    channels.setdefault(channel, set()).add(websocket)
    logger.info(
        "Client %s joined channel '%s' (size=%d)",
        getattr(websocket, "remote_address", "unknown"),
        channel,
        len(channels[channel]),
    )


async def broadcast_to_channel(channel: str, message: Dict[str, Any], sender: Any = None) -> None:
    if channel not in channels:
        logger.warning("Attempted to broadcast to non-existent channel: %s", channel)
        return

    payload = json.dumps(message)
    dead: Set[Any] = set()
    sent = 0

    for client in list(channels[channel]):
        if client is sender:
            continue
        try:
            await client.send(payload)
            sent += 1
        except websockets.exceptions.ConnectionClosed:
            dead.add(client)
        except Exception as e:
            logger.error("Error broadcasting to client: %s", e)
            dead.add(client)

    for c in dead:
        channels[channel].discard(c)
        clients.discard(c)

    if sent:
        logger.debug("Broadcasted to %d client(s) in '%s'", sent, channel)


def _get_request_path(websocket: Any) -> str:
    """Извлечь путь запроса для health-роута, совместимо с новым/старым API."""
    # websockets >= 11: websocket.request.path
    req = getattr(websocket, "request", None)
    if req is not None:
        return getattr(req, "path", "/")
    # старый API иногда прокидывал websocket.path
    return getattr(websocket, "path", "/") or "/"


async def handle_client(websocket: Any) -> None:
    """Основной обработчик клиента."""
    # health check на ws://host:port/health — сразу отвечаем и закрываем
    path = _get_request_path(websocket)
    if path == "/health":
        await websocket.send(json.dumps({
            "status": "healthy",
            "clients": len(clients),
            "channels": {name: len(m) for name, m in channels.items()},
        }))
        await websocket.close()
        return

    await register_client(websocket)

    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                logger.debug("Received from %s: %s", getattr(websocket, "remote_address", "unknown"), data)

                mtype = data.get("type")

                if mtype == "join":
                    channel = data.get("channel")
                    if channel:
                        await join_channel(websocket, channel)
                        # подтверждение join — так ожидает Figma plugin
                        response = {
                            "type": "system",
                            "channel": channel,
                            "message": {"result": {"status": "joined", "channel": channel}},
                        }
                        await websocket.send(json.dumps(response))
                        logger.info("Sent join confirmation for channel: %s", channel)
                    else:
                        await websocket.send(json.dumps({"type": "error", "message": "Channel name is required"}))

                elif mtype == "message":
                    channel = data.get("channel")
                    if channel and channel in channels:
                        await broadcast_to_channel(channel, data, websocket)
                    else:
                        await websocket.send(json.dumps({
                            "id": data.get("id"),
                            "error": f"Channel '{channel}' not found or not joined",
                        }))

                elif "id" in data and "message" in data:
                    logger.debug("Received direct message: %s", data)

                else:
                    logger.warning(
                        "Unknown message type from %s: %s",
                        getattr(websocket, "remote_address", "unknown"),
                        data.get("type", "no-type"),
                    )

            except json.JSONDecodeError as e:
                logger.error("Invalid JSON from %s: %s", getattr(websocket, "remote_address", "unknown"), e)
                try:
                    await websocket.send(json.dumps({"error": "Invalid JSON format"}))
                except Exception:
                    pass
            except Exception as e:
                logger.error("Error handling message from %s: %s", getattr(websocket, "remote_address", "unknown"), e)

    except websockets.exceptions.ConnectionClosed:
        logger.info("Client connection closed: %s", getattr(websocket, "remote_address", "unknown"))
    except Exception as e:
        logger.error("Error in client handler for %s: %s", getattr(websocket, "remote_address", "unknown"), e)
    finally:
        await unregister_client(websocket)


async def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="WebSocket server for Figma plugin and MCP communication")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (use 127.0.0.1 on Windows)")
    parser.add_argument("--port", type=int, default=3055, help="Port to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("Starting WebSocket server on %s:%d", args.host, args.port)

    stop_event = asyncio.Event()

    # Unix/macOS: аккуратные сигналы. На Windows Ctrl+C вызовет KeyboardInterrupt, чего достаточно.
    try:
        loop = asyncio.get_running_loop()
        for _sig in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None)):
            if _sig is not None:
                try:
                    loop.add_signal_handler(_sig, stop_event.set)
                except (NotImplementedError, RuntimeError):
                    pass
    except Exception:
        pass

    async with serve(
        handle_client,
        args.host,
        args.port,
        ping_interval=20,
        ping_timeout=10,
        close_timeout=10,
    ):
        logger.info("WebSocket server listening on ws://%s:%d", args.host, args.port)
        logger.info("Server ready to accept connections from Figma plugin and MCP server")

        try:
            # Ждём сигнала или Ctrl+C. Если ничего не придёт — работает бесконечно.
            await stop_event.wait()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, stopping...")
        finally:
            # Мягко закрываем всех клиентов
            for c in list(clients):
                try:
                    await c.close()
                except Exception:
                    pass
            logger.info("Server stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server interrupted")
    except Exception as e:
        logger.error("Server error: %s", e)
        sys.exit(1)
